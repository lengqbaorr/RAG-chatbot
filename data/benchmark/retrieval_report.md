| strategy | top_k | fetch_k | min_score | questions | recall@1 | recall@3 | recall@5 | mrr | precision@k | citation | keywords | unanswerable | avg_latency | failed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| parent_child | 3 | 8 | 0.76 | 100 | 0.7841 | 0.8750 | 0.8750 | 0.8144 | 0.6023 | 0.8750 | 0.6155 | 0.7500 | 0.3159s | 14 |
| dense | 3 | 8 | 0.76 | 100 | 0.6705 | 0.8295 | 0.8295 | 0.7235 | 0.5682 | 0.8295 | 0.5530 | 0.7500 | 0.2402s | 18 |

## Failed Cases

### parent_child
- `q003` [front_matter/metadata] low_score_or_empty: Nhóm thực hiện đề tài gồm những sinh viên nào? | sources=[] | pages=[] | scores=[]
- `q014` [ir_intro/goal] low_score_or_empty: Mục tiêu đề tài của nhóm là gì? | sources=[] | pages=[] | scores=[]
- `q016` [term_processing/rationale] low_score_or_empty: Vì sao nhóm quyết định không loại bỏ chữ số mà chuyển đổi chúng thành từ? | sources=[] | pages=[] | scores=[]
- `q025` [vsm/classification] wrong_section: VSM có những biến thể nào? | sources=['Test.pdf', 'Test.pdf'] | pages=['45-49', '45-49'] | scores=[0.7659, 0.7659]
- `q027` [vsm/assumption] wrong_section: Những giả định nào được đặt ra trong mô hình VSM? | sources=['Test.pdf', 'Test.pdf', 'Test.pdf'] | pages=['45-49', '45-49', '59-68'] | scores=[0.8147, 0.8147, 0.7907]
- `q036` [vsm/limitation] wrong_section: Vì sao độ đo Euclidean thường không được sử dụng trong VSM? | sources=['Test.pdf', 'Test.pdf', 'Test.pdf'] | pages=['45-49', '45-49', '73-77'] | scores=[0.7742, 0.7742, 0.7691]
- `q038` [bm25/definition] low_score_or_empty: BM25 là viết tắt của từ gì và được phát triển bởi ai? | sources=[] | pages=[] | scores=[]
- `q083` [improvement/result] wrong_section: Kết quả thực nghiệm MAP của mô hình BM25+LSA so với các phương pháp khác như thế nào? | sources=['Test.pdf', 'Test.pdf', 'Test.pdf'] | pages=['59-68', '59-68', '69-72'] | scores=[0.788, 0.788, 0.7781]
- `q084` [improvement/conclusion] wrong_section: Mô hình nào cho hiệu quả tốt nhất theo kiểm định giả thuyết trong nghiên cứu cải tiến? | sources=['Test.pdf', 'Test.pdf', 'Test.pdf'] | pages=['59-68', '59-68', '45-49'] | scores=[0.7738, 0.7738, 0.7697]
- `q085` [improvement/future_work] wrong_section: Nhóm đề xuất những hướng phát triển nào để cải tiến VSM và BM25? | sources=['Test.pdf', 'Test.pdf', 'Test.pdf'] | pages=['45-49', '45-49', '59-68'] | scores=[0.7881, 0.7881, 0.7774]
- `q088` [references/citation] low_score_or_empty: Video Youtube nào được tham khảo để giải thích Okapi BM25? | sources=[] | pages=[] | scores=[]
- `q090` [out_of_scope/unanswerable] unanswerable_not_rejected: Báo cáo có hướng dẫn cài đặt mô hình Transformer không? | sources=['Test.pdf', 'Test.pdf'] | pages=['59-68', '59-68'] | scores=[0.7605, 0.7605]
- `q095` [out_of_scope/unanswerable] unanswerable_not_rejected: Tài liệu có đề cập cụ thể đến mô hình BERT hoặc word2vec không? | sources=['Test.pdf', 'Test.pdf', 'Test.pdf'] | pages=['24-29', '24-29', '79'] | scores=[0.7834, 0.7834, 0.7822]
- `q100` [out_of_scope/unanswerable] unanswerable_not_rejected: Báo cáo có đính kèm đầy đủ mã nguồn chương trình cài đặt không? | sources=['Test.pdf', 'Test.pdf', 'Test.pdf'] | pages=['4', '4', '73-77'] | scores=[0.7779, 0.7779, 0.7678]

### dense
- `q003` [front_matter/metadata] low_score_or_empty: Nhóm thực hiện đề tài gồm những sinh viên nào? | sources=[] | pages=[] | scores=[]
- `q014` [ir_intro/goal] low_score_or_empty: Mục tiêu đề tài của nhóm là gì? | sources=[] | pages=[] | scores=[]
- `q016` [term_processing/rationale] low_score_or_empty: Vì sao nhóm quyết định không loại bỏ chữ số mà chuyển đổi chúng thành từ? | sources=[] | pages=[] | scores=[]
- `q025` [vsm/classification] wrong_section: VSM có những biến thể nào? | sources=['Test.pdf', 'Test.pdf'] | pages=['47', '47'] | scores=[0.7659, 0.7659]
- `q027` [vsm/assumption] wrong_section: Những giả định nào được đặt ra trong mô hình VSM? | sources=['Test.pdf', 'Test.pdf', 'Test.pdf'] | pages=['47', '47', '65'] | scores=[0.8147, 0.8147, 0.7907]
- `q031` [vsm/formula] wrong_section: Công thức tính idf(t,D) là gì? | sources=['Test.pdf', 'Test.pdf', 'Test.pdf'] | pages=['36', '36', '43'] | scores=[0.8006, 0.8006, 0.7999]
- `q036` [vsm/limitation] wrong_section: Vì sao độ đo Euclidean thường không được sử dụng trong VSM? | sources=['Test.pdf', 'Test.pdf', 'Test.pdf'] | pages=['47', '47', '73'] | scores=[0.7742, 0.7742, 0.7691]
- `q038` [bm25/definition] low_score_or_empty: BM25 là viết tắt của từ gì và được phát triển bởi ai? | sources=[] | pages=[] | scores=[]
- `q043` [bm25/formula] wrong_section: Công thức tham số hóa document length trong BM25 là gì? | sources=['Test.pdf', 'Test.pdf', 'Test.pdf'] | pages=['56', '56', '48'] | scores=[0.8332, 0.8332, 0.829]
- `q056` [evaluation/formula] wrong_section: Mean Average Precision (MAP) được tính như thế nào? | sources=['Test.pdf', 'Test.pdf', 'Test.pdf'] | pages=['61', '61', '63'] | scores=[0.8337, 0.8337, 0.8001]
- `q064` [experiment/comparison] wrong_section: Kết quả thực nghiệm cho thấy mô hình nào có MAP cao hơn giữa VSM và BM25? | sources=['Test.pdf', 'Test.pdf', 'Test.pdf'] | pages=['68', '68', '47'] | scores=[0.8153, 0.8153, 0.8072]
- `q083` [improvement/result] wrong_section: Kết quả thực nghiệm MAP của mô hình BM25+LSA so với các phương pháp khác như thế nào? | sources=['Test.pdf', 'Test.pdf', 'Test.pdf'] | pages=['67', '67', '68'] | scores=[0.788, 0.788, 0.7865]
- `q084` [improvement/conclusion] wrong_section: Mô hình nào cho hiệu quả tốt nhất theo kiểm định giả thuyết trong nghiên cứu cải tiến? | sources=['Test.pdf', 'Test.pdf', 'Test.pdf'] | pages=['64', '64', '47'] | scores=[0.7738, 0.7738, 0.7697]
- `q085` [improvement/future_work] wrong_section: Nhóm đề xuất những hướng phát triển nào để cải tiến VSM và BM25? | sources=['Test.pdf', 'Test.pdf', 'Test.pdf'] | pages=['47', '47', '68'] | scores=[0.7881, 0.7881, 0.7774]
- `q088` [references/citation] low_score_or_empty: Video Youtube nào được tham khảo để giải thích Okapi BM25? | sources=[] | pages=[] | scores=[]
- `q090` [out_of_scope/unanswerable] unanswerable_not_rejected: Báo cáo có hướng dẫn cài đặt mô hình Transformer không? | sources=['Test.pdf', 'Test.pdf'] | pages=['62', '62'] | scores=[0.7605, 0.7605]
- `q095` [out_of_scope/unanswerable] unanswerable_not_rejected: Tài liệu có đề cập cụ thể đến mô hình BERT hoặc word2vec không? | sources=['Test.pdf', 'Test.pdf', 'Test.pdf'] | pages=['29', '29', '79'] | scores=[0.7834, 0.7834, 0.7822]
- `q100` [out_of_scope/unanswerable] unanswerable_not_rejected: Báo cáo có đính kèm đầy đủ mã nguồn chương trình cài đặt không? | sources=['Test.pdf', 'Test.pdf', 'Test.pdf'] | pages=['4', '4', '76'] | scores=[0.7779, 0.7779, 0.7678]