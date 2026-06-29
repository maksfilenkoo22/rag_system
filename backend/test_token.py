from backend.auth.auth_service import check_access_by_token


token = input("Вставь JWT-токен: ")

result = check_access_by_token(token)

print(result)