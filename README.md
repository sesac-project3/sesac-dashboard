# Sesac Dashboard

## 로컬 개발환경

처음 실행하거나 `requirements.txt`, `package-lock.json` 등이 변경된 경우 이미지를 빌드합니다.

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

이후에는 다음 명령어로 실행합니다.

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

개발 환경에서는 Python과 React 코드 변경 사항이 자동으로 반영됩니다.
