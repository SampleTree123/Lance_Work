// Read-only independent FBX SDK normal audit for Headshot route experiments.
// This program never exports or repairs the supplied FBX.
#include <boost/json/src.hpp>
#include <fbxsdk.h>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>

namespace json = boost::json;
namespace fs = std::filesystem;

json::array normals(FbxGeometryBase* geometry, bool includeValues = false) {
    json::array result;
    for (int layer = 0; layer < geometry->GetElementNormalCount(); ++layer) {
        auto* element = geometry->GetElementNormal(layer);
        const auto& values = element->GetDirectArray();
        int nonfinite = 0, oversized = 0;
        double maximum = 0;
        json::array examples, samples;
        for (int i = 0; i < values.GetCount(); ++i) {
            const FbxVector4 n = values.GetAt(i);
            if (includeValues) {
                json::array sample;
                for (int axis = 0; axis < 3; ++axis)
                    sample.push_back(std::isfinite(n[axis]) ? json::value(n[axis]) : json::value("nonfinite"));
                samples.push_back(sample);
            }
            for (int axis = 0; axis < 3; ++axis) {
                const double x = n[axis];
                if (std::isfinite(x)) maximum = std::max(maximum, std::abs(x));
                else ++nonfinite;
                if (std::isfinite(x) && std::abs(x) > 16.0) ++oversized;
                if ((!std::isfinite(x) || std::abs(x) > 16.0) && examples.size() < 50) {
                    json::object row{{"normal_index", i}, {"axis", axis}};
                    row["value"] = std::isfinite(x) ? json::value(x) : json::value("nonfinite");
                    examples.push_back(row);
                }
            }
        }
        json::object row{{"layer", layer}, {"mapping_mode", int(element->GetMappingMode())},
            {"reference_mode", int(element->GetReferenceMode())}, {"direct_count", values.GetCount()},
            {"index_count", element->GetIndexArray().GetCount()}, {"nonfinite_components", nonfinite},
            {"abs_gt_16_components", oversized}, {"finite_max_abs", maximum}, {"examples", examples}};
        if (includeValues) row["values_xyz"] = samples;
        result.push_back(row);
    }
    return result;
}

int main(int argc, char** argv) {
    FbxManager* manager = nullptr;
    try {
        if (argc != 3 && argc != 5)
            throw std::runtime_error("Usage: probe input.fbx new_report.json [exact_node exact_shape]");
        const std::string detailNode = argc == 5 ? argv[3] : "";
        const std::string detailShape = argc == 5 ? argv[4] : "";
        const fs::path input = fs::u8path(argv[1]), output = fs::u8path(argv[2]);
        if (!fs::is_regular_file(input) || fs::exists(output))
            throw std::runtime_error("Missing input or output already exists");
        manager = FbxManager::Create();
        auto* settings = FbxIOSettings::Create(manager, IOSROOT);
        manager->SetIOSettings(settings);
        auto* scene = FbxScene::Create(manager, "headshot_read_only_normal_probe");
        auto* importer = FbxImporter::Create(manager, "");
        const auto start = std::chrono::steady_clock::now();
        if (!importer->Initialize(argv[1], -1, settings) || !importer->Import(scene))
            throw std::runtime_error(importer->GetStatus().GetErrorString());
        importer->Destroy();
        const double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        json::array records;
        int shapeCount = 0;
        for (int i = 0; i < scene->GetNodeCount(); ++i) {
            auto* node = scene->GetNode(i);
            auto* mesh = node->GetMesh();
            if (!mesh) continue;
            records.push_back(json::object{{"node", node->GetName()}, {"type", "Mesh"},
                {"geometry", mesh->GetName()}, {"control_points", mesh->GetControlPointsCount()},
                {"normal_layers", normals(mesh, detailNode == node->GetName())}});
            for (int d = 0; d < mesh->GetDeformerCount(FbxDeformer::eBlendShape); ++d) {
                auto* blend = static_cast<FbxBlendShape*>(mesh->GetDeformer(d, FbxDeformer::eBlendShape));
                for (int c = 0; c < blend->GetBlendShapeChannelCount(); ++c) {
                    auto* channel = blend->GetBlendShapeChannel(c);
                    for (int t = 0; t < channel->GetTargetShapeCount(); ++t) {
                        auto* shape = channel->GetTargetShape(t);
                        ++shapeCount;
                        records.push_back(json::object{{"node", node->GetName()}, {"type", "Shape"},
                            {"geometry", shape->GetName()}, {"channel", channel->GetName()},
                            {"target_index", t}, {"control_points", shape->GetControlPointsCount()},
                            {"normal_layers", normals(shape, detailNode == node->GetName() && detailShape == shape->GetName())}});
                    }
                }
            }
        }
        json::object report{{"source", input.u8string()}, {"sdk_version", FBXSDK_VERSION_STRING},
            {"import_seconds", seconds}, {"shape_count", shapeCount}, {"records", records},
            {"scope", "Read-only Autodesk SDK imported normals; no repair, export, or rendering acceptance"}};
        std::ofstream stream(output, std::ios::binary);
        if (!stream) throw std::runtime_error("Cannot create report");
        stream << json::serialize(report) << '\n';
        stream.close();
        if (!stream) throw std::runtime_error("Report write failed");
        manager->Destroy();
        manager = nullptr;
        std::cout << "SDK import completed; shape_count=" << shapeCount << "; seconds=" << seconds << std::endl;
        return 0;
    } catch (const std::exception& error) {
        if (manager) manager->Destroy();
        std::cerr << error.what() << std::endl;
        return 1;
    }
}
