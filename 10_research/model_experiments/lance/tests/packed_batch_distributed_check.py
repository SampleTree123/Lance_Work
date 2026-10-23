"""Two-rank DDP packed attention/loss gradients vs eight separate microsteps."""
import json,os,sys
from pathlib import Path
from types import SimpleNamespace
from contextlib import nullcontext
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'runtime/peft_0_15_2'),str(ROOT/'lance')]
import torch
import torch.distributed as dist
from torch import nn
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.checkpoint import checkpoint
from peft import LoraConfig,inject_adapter_in_model
from train.datamake_packed_batch import compute_packed_training_loss

class Attention(nn.Module):
 def __init__(self):
  super().__init__();self.qkv=nn.Linear(8,24,bias=False);self.out=nn.Linear(8,8,bias=False)
 def body(self,x,mask):
  q,k,v=self.qkv(x).chunk(3,-1)
  scores=q@k.T/(8**.5)
  y=scores.masked_fill(~mask,-torch.inf).softmax(-1)@v
  return self.out(y)
 def forward(self,x,mask):return checkpoint(self.body,x,mask,use_reentrant=False)

def main():
 torch.set_num_threads(1);dist.init_process_group('gloo');rank=dist.get_rank();world=dist.get_world_size()
 def make():
  torch.manual_seed(2026);m=Attention().double();m.requires_grad_(False)
  m=inject_adapter_in_model(LoraConfig(r=2,lora_alpha=2,target_modules=['qkv','out'],lora_dropout=0),m)
  return DDP(m.double())
 a=make()
 g=torch.Generator().manual_seed(2081+rank)
 xs=[torch.randn(3+(i+rank)%5,8,dtype=torch.float64,generator=g) for i in range(8)]
 ys=[torch.randn(x.shape,dtype=torch.float64,generator=g) for x in xs]
 ws=[torch.rand(len(x),dtype=torch.float64,generator=g)+1 for x in xs]
 for i,(x,y,w) in enumerate(zip(xs,ys,ws)):
  with a.no_sync() if i<7 else nullcontext():
   mse=(a(x,torch.ones(len(x),len(x),dtype=torch.bool))-y).square().mean(-1)
   denom=w.sum();dist.all_reduce(denom)
   ((mse*w).sum()*world/denom/8).backward()
 for batch_size in (2,4,8):
  b=make()
  for i in range(8//batch_size):
   lengths=[len(x) for x in xs[batch_size*i:batch_size*(i+1)]];x=torch.cat(xs[batch_size*i:batch_size*(i+1)]);y=torch.cat(ys[batch_size*i:batch_size*(i+1)]);w=torch.cat(ws[batch_size*i:batch_size*(i+1)])
   labels=torch.repeat_interleave(torch.arange(batch_size),torch.tensor(lengths));mask=labels[:,None]==labels[None,:]
   with b.no_sync() if i<8//batch_size-1 else nullcontext():
    mse=(b(x,mask)-y).square()
    loss,_,_,_=compute_packed_training_loss({'mse':mse,'ce':None,'frame_mse':None},lengths,SimpleNamespace(mse_weight=1),w)
    (loss/(8//batch_size)).backward()
  max_diff=0.
  for (na,pa),(nb,pb) in zip(a.named_parameters(),b.named_parameters()):
   assert na==nb
   if pa.requires_grad:
    torch.testing.assert_close(pa.grad,pb.grad,atol=1e-12,rtol=1e-10)
    max_diff=max(max_diff,(pa.grad-pb.grad).abs().max().item())
   else:assert pa.grad is None and pb.grad is None
  print(json.dumps({'rank':rank,'world':world,'batch_size':batch_size,'max_grad_difference':max_diff,'status':'passed'}),flush=True)
 dist.destroy_process_group()
if __name__=='__main__':main()
