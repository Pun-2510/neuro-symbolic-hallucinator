---
name: checkpoint-2026-09-05-grobid-integration
description: "Tuần 13: Integration Testing với GROBID - hoàn thành"
metadata:
  type: project
  date: 2026-09-05
---

# Checkpoint: Integration Testing với GROBID

## ✅ Đã hoàn thành

### 1. Test File mới
- **File:** `tests/integration/test_grobid_integration.py`
- **Tests:** 20 test cases (16 pass, 4 skipped cho real mode)
- **Mode:** Mock HTTP (không cần Docker) + Real mode (tùy chọn)

### 2. Test Coverage

| Class | Tests | Status |
|-------|-------|--------|
| TestGrobidTEIParsing | 6 | ✅ Pass |
| TestCallGrobidFulltext | 3 | ✅ Pass |
| TestDocumentParserWithMockGrobid | 2 | ✅ Pass |
| TestPipelineWithMockGrobid | 1 | ✅ Pass |
| TestRealGrobidDocker | 4 | ⏭️ Skip (cần Docker) |
| TestGrobidCache | 2 | ✅ Pass |
| TestGrobidErrorHandling | 2 | ✅ Pass |

### 3. Script Setup đã fix
- **File:** `scripts/grobid_docker_setup.sh`
- **Fix:** Override entrypoint để chạy `grobid-service-0.8.1.jar` trực tiếp
- **Ghi chú:** macOS không hỗ trợ `tini` (PR_SET_CHILD_SUBREAPER)

## 🔴 Vấn đề GROBID Docker trên macOS

GROBID Docker image `lfoppiano/grobid:0.8.1` bị killed vì OOM trên máy này.

### Root cause
- Container được giới hạn memory (có thể do Docker Desktop settings)
- GROBID cần ~2GB RAM để load tất cả ML models

### Workaround
- Sử dụng **mock mode** cho development/testing (không cần Docker)
- Script đã được fix để chạy trên máy có đủ RAM
- Khi deploy production, nên dùng Docker với `--memory=4g`

## 📋 Cách chạy tests

```bash
# Mock mode (không cần Docker)
pytest tests/integration/test_grobid_integration.py -v

# Real mode (cần GROBID Docker)
./scripts/grobid_docker_setup.sh start
export GROBID_TEST_MODE=real
export GROBID_URL=http://localhost:8070
pytest tests/integration/test_grobid_integration.py -v -k "real"
./scripts/grobid_docker_setup.sh stop

# Tất cả integration tests
pytest tests/integration/ -v
```

## 🔧 Script Commands

```bash
# Start GROBID
./scripts/grobid_docker_setup.sh start

# Check status
./scripts/grobid_docker_setup.sh status

# Stop GROBID
./scripts/grobid_docker_setup.sh stop

# View logs
./scripts/grobid_docker_setup.sh logs

# Print environment variables
./scripts/grobid_docker_setup.sh env
```

## 📊 Test Results Summary

```
16 passed, 4 skipped, 29 warnings in 0.16s
```

## 📝 Notes

1. **GrobidOutput parsing** đã hoạt động đúng với TEI XML mẫu
2. **Citation extraction** hoạt động tốt (raw_text bao gồm surrounding text)
3. **DOI extraction** hoạt động đúng
4. **Cache functionality** đã được test
5. **Error handling** đã được test (HTTP errors, timeouts, malformed XML)

## ⚠️ Known Issues

1. **GROBID Docker OOM** trên macOS - cần tăng Docker Desktop memory
2. **Deprecation warnings** trong grobid_parser.py - nên fix trong future update
3. **XXE protection** đã hoạt động - defusedxml block attacks

## 🔄 Next Steps

1. Khi có Docker đủ RAM, chạy real mode tests
2. Fix deprecation warnings trong grobid_parser.py
3. Thêm edge case tests (PDF với nhiều pages, citations không chuẩn)
