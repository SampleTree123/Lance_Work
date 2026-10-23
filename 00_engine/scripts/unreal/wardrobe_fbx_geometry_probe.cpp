// Experimental FBX geometry filtering; original exports are never modified.
#include <boost/json/src.hpp>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
#include <fbxsdk.h>

namespace json = boost::json;
namespace fs = std::filesystem;

json::array matrix(const FbxAMatrix& value) {
    json::array out;
    for (int r = 0; r < 4; ++r)
        for (int c = 0; c < 4; ++c) out.push_back(value.Get(r, c));
    return out;
}

json::object inventory(FbxScene* scene, const std::set<std::string>& selected) {
    json::array meshes, skeleton;
    for (int i = 0; i < scene->GetNodeCount(); ++i) {
        auto* node = scene->GetNode(i);
        if (node->GetSkeleton()) {
            skeleton.push_back(json::object{{"name", node->GetName()},
                {"parent", node->GetParent() ? node->GetParent()->GetName() : ""},
                {"global", matrix(node->EvaluateGlobalTransform(FBXSDK_TIME_ZERO))}});
        }
        auto* mesh = node->GetMesh();
        if (!mesh || !selected.count(node->GetName())) continue;
        json::array skins;
        for (int s = 0; s < mesh->GetDeformerCount(FbxDeformer::eSkin); ++s) {
            auto* skin = static_cast<FbxSkin*>(mesh->GetDeformer(s, FbxDeformer::eSkin));
            json::array clusters;
            for (int c = 0; c < skin->GetClusterCount(); ++c) {
                auto* cluster = skin->GetCluster(c);
                FbxAMatrix transform, link;
                cluster->GetTransformMatrix(transform);
                cluster->GetTransformLinkMatrix(link);
                json::array indices, weights;
                for (int k = 0; k < cluster->GetControlPointIndicesCount(); ++k) {
                    indices.push_back(cluster->GetControlPointIndices()[k]);
                    weights.push_back(cluster->GetControlPointWeights()[k]);
                }
                clusters.push_back(json::object{{"link", cluster->GetLink()->GetName()},
                    {"mode", int(cluster->GetLinkMode())}, {"transform", matrix(transform)},
                    {"link_transform", matrix(link)}, {"indices", indices}, {"weights", weights}});
            }
            skins.push_back(clusters);
        }
        json::array vertices, polygons, materials;
        for (int v = 0; v < mesh->GetControlPointsCount(); ++v) {
            const auto p = mesh->GetControlPointAt(v);
            vertices.push_back(json::array{p[0], p[1], p[2]});
        }
        for (int p = 0; p < mesh->GetPolygonCount(); ++p) {
            json::array face;
            for (int v = 0; v < mesh->GetPolygonSize(p); ++v)
                face.push_back(mesh->GetPolygonVertex(p, v));
            polygons.push_back(face);
        }
        for (int m = 0; m < node->GetMaterialCount(); ++m)
            materials.push_back(node->GetMaterial(m)->GetName());
        meshes.push_back(json::object{{"name", node->GetName()},
            {"vertices", vertices}, {"polygons", polygons}, {"skins", skins},
            {"materials", materials}, {"morph_deformers", mesh->GetDeformerCount(FbxDeformer::eBlendShape)},
            {"uv_elements", mesh->GetElementUVCount()}, {"normal_elements", mesh->GetElementNormalCount()},
            {"global", matrix(node->EvaluateGlobalTransform(FBXSDK_TIME_ZERO))}});
    }
    return {{"meshes", meshes}, {"skeleton", skeleton}, {"poses", scene->GetPoseCount()}};
}

int main(int argc, char** argv) {
    try {
        if (argc < 4) throw std::runtime_error("Usage: probe input.fbx output.fbx exact_mesh_node [exact_mesh_node ...]");
        fs::path input = fs::u8path(argv[1]), output = fs::u8path(argv[2]);
        if (!fs::is_regular_file(input) || fs::exists(output) || fs::exists(output.string()+".json"))
            throw std::runtime_error("Missing input or output already exists");
        std::set<std::string> requested;
        for (int i=3; i<argc; ++i)
            if (!requested.insert(argv[i]).second) throw std::runtime_error("Duplicate selection");
        auto* manager = FbxManager::Create();
        auto* settings = FbxIOSettings::Create(manager, IOSROOT);
        manager->SetIOSettings(settings);
        auto* scene = FbxScene::Create(manager, "wardrobe_probe");
        auto* importer = FbxImporter::Create(manager, "");
        auto start = std::chrono::steady_clock::now();
        if (!importer->Initialize(argv[1], -1, settings) || !importer->Import(scene))
            throw std::runtime_error(importer->GetStatus().GetErrorString());
        importer->Destroy();
        const double import_seconds = std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        std::cout << "sdk_import_seconds=" << import_seconds << std::endl;
        std::set<std::string> found;
        std::set<FbxGeometryBase*> kept;
        json::array removed;
        for (int i=0; i<scene->GetNodeCount(); ++i) {
            auto* node=scene->GetNode(i);
            if (node->GetMesh()) std::cout << "mesh_node=" << node->GetName() << std::endl;
            if (node->GetMesh() && requested.count(node->GetName())) {
                if (!found.insert(node->GetName()).second) throw std::runtime_error("Ambiguous mesh node name");
                kept.insert(node->GetMesh());
            }
        }
        if (found != requested) throw std::runtime_error("Not every exact mesh node was found");
        auto before=inventory(scene, requested);
        // Keep selected morph targets too; never destroy a selected skin or bone.
        for (auto* base : std::vector<FbxGeometryBase*>(kept.begin(), kept.end())) {
            auto* geometry=FbxCast<FbxGeometry>(base);
            for (int d=0; d<geometry->GetDeformerCount(FbxDeformer::eBlendShape); ++d) {
                auto* blend=static_cast<FbxBlendShape*>(geometry->GetDeformer(d,FbxDeformer::eBlendShape));
                for (int c=0; c<blend->GetBlendShapeChannelCount(); ++c) {
                    auto* channel=blend->GetBlendShapeChannel(c);
                    for (int t=0; t<channel->GetTargetShapeCount(); ++t) kept.insert(channel->GetTargetShape(t));
                }
            }
        }
        for (int i=scene->GetGeometryCount()-1; i>=0; --i) {
            auto* geometry=scene->GetGeometry(i);
            if (!kept.count(geometry)) {
                removed.push_back(geometry->GetName());
                geometry->Destroy();
            }
        }
        for (int i=scene->GetSrcObjectCount<FbxShape>()-1; i>=0; --i) {
            auto* shape=scene->GetSrcObject<FbxShape>(i);
            if (!kept.count(shape)) shape->Destroy();
        }
        fs::create_directories(output.parent_path());
        settings->SetBoolProp(EXP_FBX_EMBEDDED, false);
        auto* exporter=FbxExporter::Create(manager, "");
        if (!exporter->Initialize(argv[2], manager->GetIOPluginRegistry()->GetNativeWriterFormat(), settings)
            || !exporter->Export(scene)) throw std::runtime_error(exporter->GetStatus().GetErrorString());
        exporter->Destroy();
        auto* reload=FbxScene::Create(manager, "reload");
        auto* reader=FbxImporter::Create(manager, "");
        if (!reader->Initialize(argv[2], -1, settings) || !reader->Import(reload))
            throw std::runtime_error(reader->GetStatus().GetErrorString());
        auto after=inventory(reload, requested);
        bool equivalent=before == after;
        json::object report{{"scope", "experimental_geometry_filter"},
            {"source", argv[1]}, {"output", argv[2]}, {"sdk_import_seconds", import_seconds},
            {"source_bytes", fs::file_size(input)}, {"output_bytes", fs::file_size(output)},
            {"removed_geometry", removed}, {"before_export", before}, {"after_reload", after},
            {"roundtrip_equal", equivalent}, {"runtime_approved", false}};
        std::ofstream(output.string()+".json") << json::serialize(report) << '\n';
        std::cout << "roundtrip_equal=" << equivalent << " source_bytes=" << fs::file_size(input)
            << " output_bytes=" << fs::file_size(output) << " sdk_import_seconds=" << import_seconds << '\n';
        manager->Destroy();
        return equivalent ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
