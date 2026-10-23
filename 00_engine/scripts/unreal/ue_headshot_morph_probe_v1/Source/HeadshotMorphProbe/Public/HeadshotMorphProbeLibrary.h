#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "HeadshotMorphProbeLibrary.generated.h"

class USkeletalMesh;

UCLASS()
class HEADSHOTMORPHPROBE_API UHeadshotMorphProbeLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    // No writes, morph edits, asset saves or renderer side effects.
    UFUNCTION(BlueprintCallable, Category="HeadshotDiagnostics")
    static FString AuditMorphs(USkeletalMesh* Mesh);
};
