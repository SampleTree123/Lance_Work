#include "HeadshotMorphProbeLibrary.h"
#include "Animation/MorphTarget.h"
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Misc/SecureHash.h"
#include "Modules/ModuleManager.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

IMPLEMENT_MODULE(FDefaultModuleImpl, HeadshotMorphProbe)

FString UHeadshotMorphProbeLibrary::AuditMorphs(USkeletalMesh* Mesh)
{
    TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
    Root->SetBoolField(TEXT("success"), false);
    if (!Mesh || !Mesh->GetResourceForRendering() || Mesh->GetResourceForRendering()->LODRenderData.IsEmpty())
    {
        Root->SetStringField(TEXT("error"), TEXT("Missing mesh or built LOD0"));
    }
    else
    {
        const uint32 NumVertices = Mesh->GetResourceForRendering()->LODRenderData[0].GetNumVertices();
        Root->SetStringField(TEXT("mesh"), Mesh->GetPathName());
        Root->SetNumberField(TEXT("lod0_vertices"), NumVertices);
        Root->SetStringField(TEXT("scope"), TEXT("Read-only stored LOD0 morph deltas; no rendered or skinned-pose acceptance"));
        TArray<TSharedPtr<FJsonValue>> Rows;
        for (UMorphTarget* Morph : Mesh->GetMorphTargets())
        {
            if (!Morph) continue;
            auto Deltas = Morph->GetMorphTargetDeltas(0);
            FMD5 Hash;
            int64 NonfinitePosition = 0, NonfiniteNormal = 0, InvalidIndex = 0;
            double MaxPosition = 0, MaxNormal = 0;
            for (const FMorphTargetDelta& Delta : Deltas)
            {
                Hash.Update(reinterpret_cast<const uint8*>(&Delta.SourceIdx), sizeof(Delta.SourceIdx));
                if (Delta.SourceIdx >= NumVertices) ++InvalidIndex;
                const float Values[] = {Delta.PositionDelta.X, Delta.PositionDelta.Y, Delta.PositionDelta.Z,
                                        Delta.TangentZDelta.X, Delta.TangentZDelta.Y, Delta.TangentZDelta.Z};
                Hash.Update(reinterpret_cast<const uint8*>(Values), sizeof(Values));
                for (int32 Axis = 0; Axis < 6; ++Axis)
                {
                    const double Value = Values[Axis];
                    if (!FMath::IsFinite(Value))
                    {
                        if (Axis < 3) ++NonfinitePosition; else ++NonfiniteNormal;
                    }
                    else if (Axis < 3) MaxPosition = FMath::Max(MaxPosition, FMath::Abs(Value));
                    else MaxNormal = FMath::Max(MaxNormal, FMath::Abs(Value));
                }
            }
            uint8 Digest[16]; Hash.Final(Digest);
            TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
            Row->SetStringField(TEXT("name"), Morph->GetName());
            Row->SetNumberField(TEXT("delta_count"), Deltas.Num());
            Row->SetStringField(TEXT("index_position_normal_md5"), BytesToHex(Digest, 16));
            Row->SetNumberField(TEXT("nonfinite_position_components"), NonfinitePosition);
            Row->SetNumberField(TEXT("nonfinite_normal_components"), NonfiniteNormal);
            Row->SetNumberField(TEXT("invalid_source_indices"), InvalidIndex);
            Row->SetNumberField(TEXT("max_position_component_cm"), MaxPosition);
            Row->SetNumberField(TEXT("max_normal_component"), MaxNormal);
            Rows.Add(MakeShared<FJsonValueObject>(Row));
        }
        Root->SetArrayField(TEXT("morphs"), Rows);
        Root->SetBoolField(TEXT("success"), true);
    }
    FString Out;
    auto Writer = TJsonWriterFactory<>::Create(&Out);
    FJsonSerializer::Serialize(Root, Writer);
    return Out;
}
