## Reverse Engineering
![image](https://github.com/merryberry01/grape/assets/55453184/941714d9-d356-4a3a-87c2-6a7dcdfefbc1)   
공격 수행 시 적의 체력(rbp-0x14)에서 플레이어 공격력(rbp-0x10)을 뺄셈하는 로직 확인

![image](https://github.com/merryberry01/grape/assets/55453184/a6576fd1-c013-41ee-ad0b-0dd239759cf5)   
![image](https://github.com/merryberry01/grape/assets/55453184/bb6ac9c7-2d28-4308-abad-ecbc6130cb60)   
플레이어 공격력 변수 초기화 코드(main+34)에서 인자 6을 수정하면 되겠다.   

![image](https://github.com/merryberry01/grape/assets/55453184/894a42e0-54eb-46ee-aacc-858dd881375e)   
대충 100(0x64)로 변경   

![image](https://github.com/merryberry01/grape/assets/55453184/b17b1a2c-a4c1-494d-88e9-2c5dda57aaac)   
리버싱 성공

## Webhacking 1. Broken Access Control Vulnerability
### Case 1. 코드를 🐕같이 작성
![image](https://github.com/merryberry01/grape/assets/55453184/f6b85aba-ccb5-42f9-b21c-2dbfb77e2723)   
코드를 이상하게 작성한 경우.. password 몰라도 로그인 가능
### Case 2. 엔드포인트 접근 권한 필터링 부재
![image](https://github.com/merryberry01/grape/assets/55453184/79f454ae-5f0e-417b-8af3-13007aaae745)   
엔드포인트 경로만 알면 로그인 과정 없이 접근 가능

## Webhacking 2. Cookie
### Case 1. Cookie의 존재만 확인
![image](https://github.com/merryberry01/grape/assets/55453184/d858ecf1-98e8-45a8-8fb2-ef518d18b8b5)   
'user' Cookie만 있으면 pass   
![image](https://github.com/merryberry01/grape/assets/55453184/c0f83ef0-13b5-4116-9a60-0033a9052081)   
개발자 기능에서 Cookie 추가 (Value는 임의의 값으로..)
### Case 2. 유추 가능한 Value
![image](https://github.com/merryberry01/grape/assets/55453184/f14b87a3-285f-442a-ae17-17401e961795)   
babo로 로그인했을 떄 쿠키의 Value가 babo_cookie -> grape로 로그인하면 grape_cookike가 value로 설정될 가능성 존재   
엔드포인트 또한 page-babo.php 대신 page-grape.php로 접근하면 되겠다.   
![image](https://github.com/merryberry01/grape/assets/55453184/a5354c75-c8c5-40f5-bdff-927a98797ca7)   
Cookie 변조 후 접근 성공
### Case 3. Brute Force
![image](https://github.com/merryberry01/grape/assets/55453184/00688828-ab2f-48ff-9225-bb9e81846b9f)   
Cookie Value 뒤에 두 자리의 random alphabet 추가 -> grape_XX로 무차별 대입 -> status_code 200 받으면 성공   
![image](https://github.com/merryberry01/grape/assets/55453184/2e1615b0-6d9e-4099-ab7c-c3fea769a819)   
![image](https://github.com/merryberry01/grape/assets/55453184/4e274139-178a-4852-81d2-8b1aad6543bd)   
brute force로 Value 찾아낸 후 grape로 접속 성공

## Webhacking 3. Session
세션 파일(서버), 세션 쿠키(브라우저)가 한 쌍으로 동일한 세션 ID를 공유   
![image](https://github.com/merryberry01/grape/assets/55453184/eaca15af-d776-46e1-b35e-7193f1ed4b46)   
php에서 생성한 세션 ID   
![image](https://github.com/merryberry01/grape/assets/55453184/869f880b-eee3-45ef-8ddd-04f67e62f6ed)   
babo로 로그인 시 세션 ID가 이름인 세션 파일에 babo의 ID 저장   
다른 사용자의 세션 값을 알면 계정 탈취 가능: Session Hijacking

## Webhacking 4. SQL Injection
![image](https://github.com/merryberry01/grape/assets/55453184/5750d1a7-e615-4293-bb10-06f4082ab7b5)   
SELECT * FROM users WHERE username='grape'--'~일 경우, password 무시   
![image](https://github.com/merryberry01/grape/assets/55453184/db086a2a-bdb0-4879-9187-087035b043d3)   
![image](https://github.com/merryberry01/grape/assets/55453184/71d306ba-bb96-42a0-b40c-943812b1af13)   
로그인 성공   
이를 막기 위해 입력값을 검사하여 주석, 특수문자 등을 제거

## Remote Access Trojan
![image](https://github.com/merryberry01/grape/assets/55453184/c18528e4-6d0b-4e4e-a053-54685d17b248)   
리버스 쉘 실습
