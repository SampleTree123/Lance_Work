#include <fbxsdk.h>

#include <cstring>
#include <iostream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace {

constexpr const char* kLegacyPrefix = "cc_base_";

struct RenameRecord {
    std::string old_name;
    std::string new_name;
};

std::string TargetName(const char* node_name) {
    const std::string name = node_name ? node_name : "";
    if (name.rfind(kLegacyPrefix, 0) != 0) {
        return name;
    }
    std::string stripped = name.substr(std::strlen(kLegacyPrefix));
    // The converted UE5 skeleton keeps the CC hip as pelvis and maps the
    // secondary CC pelvis helper to pelvis_0.
    if (stripped == "pelvis") {
        return "pelvis_0";
    }
    return stripped;
}

void CollectNodes(FbxNode* node, std::vector<FbxNode*>& nodes) {
    if (!node) {
        return;
    }
    nodes.push_back(node);
    for (int index = 0; index < node->GetChildCount(); ++index) {
        CollectNodes(node->GetChild(index), nodes);
    }
}

int Run(const char* input_path, const char* output_path) {
    FbxManager* manager = FbxManager::Create();
    if (!manager) {
        std::cerr << "Unable to create FBX manager.\n";
        return 2;
    }
    FbxIOSettings* io_settings = FbxIOSettings::Create(manager, IOSROOT);
    manager->SetIOSettings(io_settings);

    FbxImporter* importer = FbxImporter::Create(manager, "");
    if (!importer->Initialize(input_path, -1, manager->GetIOSettings())) {
        std::cerr << "Unable to initialize FBX import: "
                  << importer->GetStatus().GetErrorString() << "\n";
        importer->Destroy();
        manager->Destroy();
        return 3;
    }
    FbxScene* scene = FbxScene::Create(manager, "motion_scene");
    if (!importer->Import(scene)) {
        std::cerr << "Unable to import FBX: "
                  << importer->GetStatus().GetErrorString() << "\n";
        importer->Destroy();
        manager->Destroy();
        return 4;
    }
    importer->Destroy();

    std::vector<FbxNode*> nodes;
    CollectNodes(scene->GetRootNode(), nodes);
    std::unordered_map<std::string, FbxNode*> names;
    for (FbxNode* node : nodes) {
        const std::string name = node->GetName();
        if (!name.empty() && names.find(name) == names.end()) {
            names.emplace(name, node);
        }
    }

    std::vector<RenameRecord> pending;
    for (FbxNode* node : nodes) {
        const std::string old_name = node->GetName();
        const std::string new_name = TargetName(old_name.c_str());
        if (new_name == old_name) {
            continue;
        }
        const auto collision = names.find(new_name);
        if (collision != names.end() && collision->second != node) {
            std::cerr << "Rename collision: " << old_name << " -> "
                      << new_name << "\n";
            manager->Destroy();
            return 5;
        }
        pending.push_back({old_name, new_name});
    }

    std::unordered_map<std::string, std::string> rename_map;
    for (const RenameRecord& record : pending) {
        rename_map.emplace(record.old_name, record.new_name);
    }
    for (FbxNode* node : nodes) {
        const auto found = rename_map.find(node->GetName());
        if (found == rename_map.end()) {
            continue;
        }
        const std::string old_name = found->first;
        const std::string new_name = found->second;
        node->SetName(new_name.c_str());
        FbxNodeAttribute* attribute = node->GetNodeAttribute();
        if (attribute && std::string(attribute->GetName()) == old_name) {
            attribute->SetName(new_name.c_str());
        }
    }

    int remaining_prefixed = 0;
    for (FbxNode* node : nodes) {
        if (std::string(node->GetName()).rfind(kLegacyPrefix, 0) == 0) {
            ++remaining_prefixed;
        }
    }
    if (pending.empty() || remaining_prefixed != 0) {
        std::cerr << "Unexpected normalization result: renamed="
                  << pending.size() << ", remaining_prefixed="
                  << remaining_prefixed << "\n";
        manager->Destroy();
        return 6;
    }

    FbxExporter* exporter = FbxExporter::Create(manager, "");
    if (!exporter->Initialize(output_path, -1, manager->GetIOSettings())) {
        std::cerr << "Unable to initialize FBX export: "
                  << exporter->GetStatus().GetErrorString() << "\n";
        exporter->Destroy();
        manager->Destroy();
        return 7;
    }
    if (!exporter->Export(scene)) {
        std::cerr << "Unable to export FBX: "
                  << exporter->GetStatus().GetErrorString() << "\n";
        exporter->Destroy();
        manager->Destroy();
        return 8;
    }
    exporter->Destroy();

    std::cout << "NODE_COUNT\t" << nodes.size() << "\n";
    std::cout << "RENAMED_COUNT\t" << pending.size() << "\n";
    std::cout << "REMAINING_PREFIXED\t" << remaining_prefixed << "\n";
    for (const RenameRecord& record : pending) {
        std::cout << "RENAME\t" << record.old_name << "\t"
                  << record.new_name << "\n";
    }
    manager->Destroy();
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "Usage: fbx_motion_normalizer <input.fbx> <output.fbx>\n";
        return 1;
    }
    return Run(argv[1], argv[2]);
}
