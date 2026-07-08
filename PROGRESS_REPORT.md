# Progress Report

Ngày cập nhật: 2026-07-08

## Mục Tiêu

Xây dựng RAG chatbot cho tài liệu cá nhân theo pipeline:

```text
Loader -> Chunking -> Embedding -> Vector Store -> Retrieval -> Generation
```

Hiện đã hoàn thành nền tảng project, document loader và chunking pipeline.

## 1. Nền Tảng Project

Đã hoàn thành:

- FastAPI app skeleton.
- Config qua `.env`.
- Health check endpoint.
- Schema nền cho document, chat, health.
- Virtual environment `.venv`.
- Dependency cho RAG, parsing tài liệu, OCR, vector DB và test.

Kiểm tra hiện tại:

```text
pytest: 32 passed
```

## 2. Document Loader

Đã hỗ trợ:

- `.txt`
- `.md`
- `.pdf`
- `.docx`
- HTML URL
- Image OCR: `.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`, `.bmp`, `.gif`, `.webp`

OCR:

- Dùng `pytesseract`.
- Tesseract đã chạy được.
- Đã có language data:

```text
eng
osd
vie
```

`.env` hiện dùng:

```env
OCR_LANGUAGES="eng+vie"
```

Test với PDF thật:

```text
23520108_23520383_23521714.pdf
```

Kết quả:

```text
pdf_total_pages=23
loaded_documents=23
total_chars=21806
```

Kết luận: loader đã đủ tốt để làm input cho chunking.

## 3. Chunking Pipeline

Pipeline hiện tại:

```text
Document
  -> TextNormalizer
  -> StructureParser
  -> RecursiveTokenSplitter / MarkdownHeadingSplitter
  -> SmallChunkMerger
  -> ParentChunkBuilder
  -> ChunkValidator
  -> DocumentChunk
```

Đã có các thành phần:

- `DocumentChunk`
- `ChunkMetadata`
- `StructuredUnit`
- `ContentType`
- `ChunkingStrategy`
- `TextNormalizer`
- `StructureParser`
- `RecursiveTokenSplitter`
- `MarkdownHeadingSplitter`
- `SmallChunkMerger`
- `ParentChunkBuilder`
- `ChunkQualityReporter`
- `RetrievalEvaluator`
- `LexicalChunkRetriever`

Metadata chunk hiện có:

- `source_id`
- `source_name`
- `source_type`
- `page_start`
- `page_end`
- `section_title`
- `header_path`
- `chunk_index`
- `token_count`
- `content_hash`
- `parent_id`
- `child_ids`
- `content_type`
- `language`
- `chunk_level`
- `embedding_text_hash`
- `parser_version`
- `chunker_version`

## 4. Cải Tiến Chunking Đã Làm

Đã fix heading detection cho PDF:

- Không nhận công thức có `=` làm heading.
- Không nhận text có nhiều ký hiệu toán học làm heading.
- Không nhận text có tỷ lệ số/ký hiệu cao làm heading.

Ví dụ đã xử lý:

```text
5 A = 2s2√3
```

không còn bị nhận nhầm là heading.

Đã thêm:

- `content_type`: `cover`, `body`, `table`, `code`, `toc`, `reference`, `ocr`.
- Section context trong chunk text:

```text
Section: h1 > h2 > h3

<content>
```

- Merge chunk nhỏ tương thích.
- Quality report cho chunking.
- Parent-child chunking support.
- Section-first parent builder dùng hard boundary: không merge parent qua section khác.
- Parent section key gom các subsection cùng section cha, ví dụ `2.1.*`, nhưng không trộn sang `2.2.*`.
- Parent overlap nhẹ bằng text tail, mặc định `120` tokens.
- Không tạo parent chunk nếu chỉ bọc đúng 1 child và không bổ sung ngữ cảnh, tránh duplicate parent-child.
- Parent metadata dùng common parent section/header path thay vì lấy subsection cuối.
- `retrieval_excluded` cho `cover`, `toc`, `reference` để loại khỏi retrieval mặc định nhưng vẫn giữ metadata/citation.
- Retrieval evaluation baseline với `Recall@K`, `MRR`, `Citation Accuracy`.

## 5. Kết Quả Chunking PDF Thật

File:

```text
23520108_23520383_23521714.pdf
```

Cấu hình:

```text
chunk_size_tokens=450
chunk_overlap_tokens=60
```

Kết quả:

```text
documents: 23
total_chunks: 24
tokens: min=83 p50=287 p90=384 max=445 avg=266.71
chunks_under_100: 2
chunks_over_900: 0
empty_chunks: 0
duplicate_chunks: 0
suspected_formula_headings: 0
retrieval_excluded_chunks: 1
content_type_distribution: {'cover': 1, 'body': 22, 'table': 1}
source_type_distribution: {'pdf': 24}
```

Nhận xét:

- Formula heading false positive đã được xử lý.
- Citation theo page còn rõ ràng.
- Chunk hiện hơi nhỏ vì PDF loader đang tách mỗi page thành một `Document`.
- Nếu muốn chunk trung bình lớn hơn, nên làm parent-child retrieval hoặc file-level grouping có page range rõ ràng.

Khi bật parent chunks:

```powershell
.\.venv\Scripts\python.exe scripts\print_chunks.py --parents --level parent --limit 2
```

Kết quả hiện tại với section-first parent builder:

```text
total_chunks: 31
chunk_level_distribution: {'child': 24, 'parent': 7}
p90_tokens: 780
max_tokens: 1089
duplicate_chunks: 0
retrieval_excluded_chunks: 1
content_type_distribution: {'cover': 1, 'body': 29, 'table': 1}
```

Ý nghĩa:

- Search sau này nên dùng child chunks.
- Khi generate answer, có thể lấy parent chunk tương ứng để cung cấp ngữ cảnh rộng hơn.

## 6. Script Hỗ Trợ

Đã có:

```text
scripts/print_chunks.py
scripts/evaluate_retrieval.py
data/evaluation/sample_questions.jsonl
```

Dùng để:

- load tài liệu
- chunk tài liệu
- in metadata từng chunk
- in quality report
- in riêng `child` hoặc `parent` chunks

Ví dụ:

```powershell
.\.venv\Scripts\python.exe scripts\print_chunks.py --limit 3
```

Chạy retrieval evaluation baseline:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_retrieval.py --k 5
```

Kết quả lexical baseline hiện tại trên 3 câu hỏi mẫu:

```text
recall_at_k: 1.0
mrr: 0.5833
citation_accuracy: 1.0
unanswered_questions: 0
```

## 7. Test

Tổng test hiện tại:

```text
32 passed
```

Bao gồm:

- Health API test.
- Loader tests.
- TXT/MD/DOCX/PDF/URL loader tests.
- Chunking tests.
- Formula heading test.
- Small chunk merge test.
- Parent-child chunking test.
- Section-first parent builder test.
- Parent overlap test.
- Retrieval exclusion test.
- Retrieval evaluation metric test.
- Content type test.
- Quality report test.
- PDF thật chunking test.

## 8. Chưa Làm

Chưa làm:

- Embedding pipeline.
- ChromaDB local vector store.
- Pinecone integration.
- Retrieval API.
- RAG answer generation.
- Parent-child retrieval.
- Evaluation set cho retrieval.

## 9. Bước Tiếp Theo

Thứ tự đề xuất:

1. Xây embedding interface.
2. Tạo local ChromaDB vector store.
3. Index `DocumentChunk`.
4. Tạo retriever query top-k.
5. Trả về answer kèm source citation.
6. Sau đó tối ưu parent-child retrieval và evaluation.
