import sys
sys.path.append("/app")

from services.weaviate_client import db
from services.clip_embedder import clip_embedder

q = "show Single Scan Semantic Segmentation"
clip_v = clip_embedder.get_text_embedding_for_clip(q)

print(f"Clip Vector length: {len(clip_v)}")

res = db.search_all_classes(clip_v, clip_vector=clip_v, limit=2)
print(f"Number of total items: {len(res)}")
for r in res:
    print(f"Modality: {r.get('modality')}, Score: {r.get('score')}")
    if r.get('modality') == 'image':
        print(f"Caption: {r.get('caption')}")
