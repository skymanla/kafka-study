# kafka-study
- kafka를 docker로 올리는 연습
- open ui source 탐방(?)

## 구동
```
docker compose -f {사용할 yml} up -d --build
```
- python 가상환경 구성
```
python3 -m venv venv && source venv/bin/activate
```
- package install
```
pip install -r requirements.txt
```
- code runner
```
./{python_file}.py getting_started.ini
```

## 유의사항
- 현재 `docker-compose-conduktor.yml`은 오류가 발생하여 수정 중

## 구동 확인
- `kafdrop.yml`
- `kafka-ui.yml`
- `kafka-ui-minimal.yml`
- `kafka-bitnami.yml`
