STT	Task	File	Effort	Dependency
1	Tạo source_normalizer.py	transform/src/io/source_normalizer.py	1 giờ	–
2	Cập nhật reader.py đọc multi-source	transform/src/io/reader.py	1.5 giờ	Task 1
3	Cập nhật salary.py support pre-parsed	transform/src/processors/salary.py	1 giờ	Task 2
4	Cập nhật skills.py support pre-extracted	transform/src/processors/skills.py	1 giờ	Task 2
5	Cập nhật SilverJob schema	transform/src/schemas/silver_schema.py	30 phút	–
6	Cập nhật process_record() trong pipeline.py	transform/src/orchestrator/pipeline.py	30 phút	Task 1-5
7	Kiểm thử với cả 2 sources	–	1 giờ	Task 1-6