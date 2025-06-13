# SSH Setup для Raspberry Pi5 - Пошаговые команды

## Параметры подключения
- **IP**: 192.168.1.234
- **Пользователь**: standa
- **Пароль**: crossover
- **Имя хоста**: bedrock
- **Имя ключа**: bedrock_rsa

## Команды для выполнения в PowerShell

### 1. Создание SSH ключа
```powershell
ssh-keygen -t rsa -b 4096 -f "$env:USERPROFILE\.ssh\bedrock_rsa" -N '""' -C "standa@bedrock"
```

### 2. Копирование публичного ключа на Pi
```powershell
$pubKey = Get-Content "$env:USERPROFILE\.ssh\bedrock_rsa.pub" -Raw
ssh standa@192.168.1.234 "mkdir -p ~/.ssh && echo '$pubKey' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```
**⚠️ При выполнении этой команды введите пароль: `crossover`**

### 3. Создание SSH config файла
```powershell
@"
Host bedrock
    HostName 192.168.1.234
    User standa
    IdentityFile ~/.ssh/bedrock_rsa
    StrictHostKeyChecking no
    IdentitiesOnly yes

Host 192.168.1.234
    User standa
    IdentityFile ~/.ssh/bedrock_rsa
    StrictHostKeyChecking no
    IdentitiesOnly yes
"@ | Out-File "$env:USERPROFILE\.ssh\config" -Encoding UTF8
```

### 4. Тестирование подключения
```powershell
ssh bedrock
```

### 5. Проверка содержимого файлов (опционально)
```powershell
# Проверка созданных ключей
ls "$env:USERPROFILE\.ssh\"

# Просмотр SSH config
Get-Content "$env:USERPROFILE\.ssh\config"

# Просмотр публичного ключа
Get-Content "$env:USERPROFILE\.ssh\bedrock_rsa.pub"
```

## Настройка статического IP на Raspberry Pi5

После успешного подключения выполните на Pi:

### 1. Редактирование конфигурации DHCP
```bash
sudo nano /etc/dhcpcd.conf
```

### 2. Добавьте в конец файла
```bash
# Static IP configuration for bedrock
interface eth0
static ip_address=192.168.1.234/24
static routers=192.168.1.254
static domain_name_servers=192.168.1.254 8.8.8.8

# Резервное подключение по Wi-Fi (если нужно)
interface wlan0
static ip_address=192.168.1.234/24
static routers=192.168.1.254
static domain_name_servers=192.168.1.254 8.8.8.8
```

### 3. Перезагрузка Pi
```bash
sudo reboot
```

## Настройка VS Code

### 1. Установка расширения
- Откройте VS Code
- Перейдите в Extensions (Ctrl+Shift+X)
- Найдите и установите **Remote - SSH**

### 2. Подключение к Pi
- Нажмите **F1**
- Выберите **Remote-SSH: Connect to Host...**
- Выберите **bedrock** из списка или введите `192.168.1.234`
- VS Code подключится без запроса пароля

## Полезные команды

### Подключение к Pi
```powershell
# По имени хоста
ssh bedrock

# По IP адресу
ssh standa@192.168.1.234
```

### Копирование файлов
```powershell
# Копирование файла на Pi
scp file.txt bedrock:~/

# Копирование файла с Pi
scp bedrock:~/file.txt ./

# Копирование папки
scp -r folder/ bedrock:~/
```

### Выполнение команд на Pi
```powershell
# Выполнение одной команды
ssh bedrock "ls -la"

# Проверка статуса Pi
ssh bedrock "uptime && df -h"
```

## Устранение проблем

### Если подключение не работает
```powershell
# Проверка SSH ключей
ssh -v bedrock

# Принудительное использование конкретного ключа
ssh -i "$env:USERPROFILE\.ssh\bedrock_rsa" standa@192.168.1.234

# Очистка known_hosts (если IP изменился)
ssh-keygen -R 192.168.1.234
ssh-keygen -R bedrock
```

### Если нужно пересоздать ключ
```powershell
# Удаление старых ключей
rm "$env:USERPROFILE\.ssh\bedrock_rsa*"

# Создание нового ключа
ssh-keygen -t rsa -b 4096 -f "$env:USERPROFILE\.ssh\bedrock_rsa" -N '""' -C "standa@bedrock"
```

### Проверка состояния SSH на Pi
```bash
# На Raspberry Pi выполните:
sudo systemctl status ssh
sudo systemctl enable ssh
sudo systemctl start ssh
```

## Результат

После выполнения всех команд:

✅ **SSH подключение без пароля**: `ssh bedrock`  
✅ **VS Code Remote-SSH работает**  
✅ **Фиксированный IP на Pi**: 192.168.1.234  
✅ **Копирование файлов**: `scp file.txt bedrock:~/`

## Безопасность

Созданные ключи находятся в:
- **Приватный ключ**: `C:\Users\standa\.ssh\bedrock_rsa`
- **Публичный ключ**: `C:\Users\standa\.ssh\bedrock_rsa.pub`

**Никогда не делитесь приватным ключом!**