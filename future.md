📋 Danh sách công việc Sprint 1
STT	Task	File cần sửa	Mô tả ngắn
1	get_role_from_title() return None thay vì "Data Engineer"	transform/src/utils/config.py	Tránh gán sai role cho job không phải Data
2	check_completeness() không override param	transform/src/quality/completeness.py	Đảm bảo field_error_thresholds từ config được tôn trọng
3	Mở rộng LOCATION_MAPPING với alias	transform/src/utils/config.py	Chuẩn hóa địa điểm tốt hơn (TP.HCM, HCM, HN...)
4	timeliness.py không mutate input DataFrame	transform/src/quality/timeliness.py	Tránh side effect ảnh hưởng đến pipeline
5	Tách typer khỏi runner.py	transform/src/quality/runner.py	Dùng logging thay vì typer.secho (clean architecture)
6	Tách COMPANY_NAMES_TO_FILTER khỏi STOPWORDS_VI	transform/src/utils/config.py	Phân loại đúng, tránh nhiễu khi xử lý skill
7	Fix docstring position trong check_completeness()	transform/src/quality/completeness.py	Đưa docstring lên trước code để Python nhận diện
