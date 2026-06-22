📋 Danh sách Task Sprint 3 (Gold Layer)
Dựa trên thiết kế đã thống nhất, tôi chia thành 9 task cụ thể:

STT	Task	File	Mô tả	Ưu tiên	Effort
1	Tạo module Gold và cấu trúc thư mục	transform/src/gold/ + __init__.py	Tạo thư mục và các file __init__.py	Cao	10 phút
2	fact_skills – explode skills	transform/src/gold/tables/fact_skills.py	Explode skills list → mỗi skill một row, thêm week	Cao	1 giờ
3	agg_salary – thống kê lương	transform/src/gold/tables/agg_salary.py	Group by role + seniority + week → median, p25, p75, count	Cao	1 giờ
4	agg_location – phân bố địa điểm	transform/src/gold/tables/agg_location.py	Group by location + role → job_count	Trung bình	45 phút
5	agg_trend – xu hướng theo thời gian	transform/src/gold/tables/agg_trend.py	Group by week + role → job_count	Trung bình	30 phút
6	builder.py – điều phối xây dựng Gold	transform/src/gold/builder.py	Đọc Silver, gọi các hàm trên, ghi Parquet	Cao	1.5 giờ
7	Tích hợp Gold vào pipeline.py	transform/src/orchestrator/pipeline.py	Gọi build_gold() sau transform, có config enable/disable	Cao	30 phút
8	CLI command gold	cli.py	Thêm lệnh uv run python cli.py gold để rebuild riêng	Trung bình	30 phút
9	Cập nhật Dashboard đọc từ Gold	dashboard/app.py	Thay đổi logic đọc từ Gold thay vì Silver	Cao	2 giờ
10	Cập nhật config.yaml và kiểm thử	config.yaml	Thêm section gold với cấu hình	Thấp	15 phút