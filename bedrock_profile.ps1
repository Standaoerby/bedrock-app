# Microsoft.PowerShell_profile.ps1 - PowerShell профиль для bedrock-app
# Добавьте в $PROFILE: . "C:\_PROJECTS\bedrock-app\bedrock_profile.ps1"

# Конфигурация проекта
$Global:BEDROCK_PI_HOST = "192.168.1.234"
$Global:BEDROCK_PI_USER = "standa"
$Global:BEDROCK_PI_PATH = "~/bedrock-app"
$Global:BEDROCK_LOCAL_PATH = "C:\_PROJECTS\bedrock-app"
$Global:BEDROCK_GIT_REPO = "http://github.com/Standaoerby/bedrock-app/"

# Функции-алиасы для Claude патчей
function cp-setup { .\claude_apply.ps1 setup }
function cp-check { .\claude_apply.ps1 check }
function cp-apply { .\claude_apply.ps1 apply }
function cp-sync { .\claude_apply.ps1 sync }
function cp-deploy { .\claude_apply.ps1 deploy }
function cp-rollback { param($n=1) .\claude_apply.ps1 rollback $n }
function cp-test { Test-NetConnection -ComputerName $BEDROCK_PI_HOST -Port 22 }

# SSH команды для Pi
function ssh-pi { ssh "standa@192.168.1.234" }
function ssh-pi-logs { ssh "standa@192.168.1.234" "cd ~/bedrock-app && tail -f *.log" }
function ssh-pi-status { ssh "standa@192.168.1.234" "cd ~/bedrock-app && git status" }

# Rsync команды (требует rsync for Windows или WSL)
function sync-to-pi { 
    rsync -avz --exclude=.git --exclude=__pycache__ ./ "standa@192.168.1.234:~/bedrock-app/"
}
function sync-patches { 
    rsync -avz claude_patches/ "standa@192.168.1.234:~/bedrock-app/claude_patches/"
}
function sync-from-pi { 
    rsync -avz "standa@192.168.1.234:~/bedrock-app/" ./ --exclude=.git
}

# Git команды
function git-push-bedrock { 
    git add .
    git commit -m "Update from Windows $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    git push origin main
}
function git-pull-bedrock { git pull origin main }
function git-status-pi { ssh "standa@192.168.1.234" "cd ~/bedrock-app && git status" }
function git-pull-pi { ssh "standa@192.168.1.234" "cd ~/bedrock-app && git pull origin main" }

# Комбинированные workflow
function full-sync {
    Write-Host "🚀 Запуск полной синхронизации..." -ForegroundColor Cyan
    cp-apply
    git-push-bedrock
    sync-to-pi
    git-pull-pi
    Write-Host "✅ Полная синхронизация завершена!" -ForegroundColor Green
}

function quick-deploy {
    Write-Host "⚡ Быстрый деплой..." -ForegroundColor Cyan
    sync-to-pi
    ssh "standa@192.168.1.234" "cd ~/bedrock-app && ./claude_apply.sh apply"
    Write-Host "✅ Быстрый деплой завершен!" -ForegroundColor Green
}

# Python команды на Pi
function pi-python { param($script) ssh "standa@192.168.1.234" "cd ~/bedrock-app && python3 $script" }
function pi-pip { param($package) ssh "standa@192.168.1.234" "cd ~/bedrock-app && pip3 $package" }
function pi-run { ssh "standa@192.168.1.234" "cd ~/bedrock-app && python3 main.py" }

# Мониторинг Pi
function pi-htop { ssh "standa@192.168.1.234" "htop" }
function pi-temp { ssh "standa@192.168.1.234" "vcgencmd measure_temp" }
function pi-gpio { ssh "standa@192.168.1.234" "gpio readall" }
function pi-processes { ssh "standa@192.168.1.234" "ps aux | grep python" }

# Логирование и отладка
function pi-logs { ssh "standa@192.168.1.234" "cd ~/bedrock-app && tail -n 50 *.log" }
function pi-errors { ssh "standa@192.168.1.234" "cd ~/bedrock-app && grep ERROR *.log | tail -20" }
function pi-debug { ssh "standa@192.168.1.234" "cd ~/bedrock-app && python3 -u main.py" }

# VS Code интеграция
function code-bedrock { code "C:\_PROJECTS\bedrock-app" }
function code-pi { code --remote "ssh-remote+standa@192.168.1.234" "~/bedrock-app" }

# Функция помощи
function bedrock-help {
    Write-Host "🚀 Bedrock App - Быстрые команды PowerShell:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "CLAUDE ПАТЧИ:" -ForegroundColor Yellow
    Write-Host "  cp-setup     - Настройка структуры"
    Write-Host "  cp-check     - Проверка патчей"
    Write-Host "  cp-apply     - Применение патчей"
    Write-Host "  cp-sync      - Полная синхронизация"
    Write-Host "  cp-deploy    - Деплой на Pi"
    Write-Host ""
    Write-Host "SSH & RSYNC:" -ForegroundColor Yellow
    Write-Host "  ssh-pi       - Подключение к Pi"
    Write-Host "  sync-to-pi   - Синхронизация на Pi"
    Write-Host "  sync-from-pi - Получение с Pi"
    Write-Host ""
    Write-Host "GIT:" -ForegroundColor Yellow
    Write-Host "  git-push-bedrock - Коммит и push"
    Write-Host "  git-pull-pi      - Pull на Pi"
    Write-Host ""
    Write-Host "МОНИТОРИНГ PI:" -ForegroundColor Yellow
    Write-Host "  pi-temp      - Температура CPU"
    Write-Host "  pi-htop      - Процессы"
    Write-Host "  pi-logs      - Логи приложения"
    Write-Host ""
    Write-Host "WORKFLOW:" -ForegroundColor Yellow
    Write-Host "  full-sync    - Применить + commit + deploy + pull"
    Write-Host "  quick-deploy - Быстрый деплой и применение"
    Write-Host ""
    Write-Host "VS CODE:" -ForegroundColor Yellow
    Write-Host "  code-bedrock - Открыть локальный проект"
    Write-Host "  code-pi      - Открыть проект на Pi через SSH"
}

# Функция проверки статуса
function bedrock-status {
    Write-Host "🔍 Проверка статуса Bedrock App..." -ForegroundColor Cyan
    Write-Host ""
    
    # Локальный git статус
    Write-Host "📂 Локальный статус:" -ForegroundColor Yellow
    git status --porcelain
    Write-Host ""
    
    # Соединение с Pi
    Write-Host "🔗 Соединение с Pi:" -ForegroundColor Yellow
    if (Test-NetConnection -ComputerName $BEDROCK_PI_HOST -Port 22 -WarningAction SilentlyContinue).TcpTestSucceeded {
        Write-Host "✅ Pi доступен" -ForegroundColor Green
        
        # Git статус на Pi
        Write-Host ""
        Write-Host "📂 Git статус на Pi:" -ForegroundColor Yellow
        try {
            ssh "standa@192.168.1.234" "cd ~/bedrock-app && git status --porcelain"
        }
        catch {
            Write-Host "❌ Ошибка подключения" -ForegroundColor Red
        }
        
        # Температура Pi
        Write-Host ""
        Write-Host "🌡️  Температура Pi:" -ForegroundColor Yellow
        try {
            ssh "standa@192.168.1.234" "vcgencmd measure_temp"
        }
        catch {
            Write-Host "❌ Ошибка получения данных" -ForegroundColor Red
        }
    }
    else {
        Write-Host "❌ Pi недоступен" -ForegroundColor Red
    }
}

# Функция для создания патча из diff в PowerShell
function Create-PatchFromDiff {
    param(
        [string]$OldFile,
        [string]$NewFile,
        [string]$PatchName
    )
    
    if (-not $OldFile -or -not $NewFile -or -not $PatchName) {
        Write-Host "Использование: Create-PatchFromDiff -OldFile <старый> -NewFile <новый> -PatchName <имя>" -ForegroundColor Yellow
        return
    }
    
    # Использование git diff для создания патча
    git diff --no-index $OldFile $NewFile > "claude_patches\$PatchName.patch"
    Write-Host "✅ Патч создан: claude_patches\$PatchName.patch" -ForegroundColor Green
}

# Функция для быстрого создания патча из Claude
function Claude-ToPatch {
    param([string]$PatchName)
    
    if (-not $PatchName) {
        Write-Host "Использование: Claude-ToPatch <имя_патча>" -ForegroundColor Yellow
        Write-Host "Затем вставьте diff от Claude и нажмите Ctrl+Z, Enter" -ForegroundColor Cyan
        return
    }
    
    Write-Host "📝 Вставьте diff от Claude (Ctrl+Z, Enter для завершения):" -ForegroundColor Cyan
    $content = @()
    do {
        $line = Read-Host
        if ($line -ne $null) { $content += $line }
    } while ($line -ne $null -and $line -ne "")
    
    $content | Out-File -FilePath "claude_patches\$PatchName.patch" -Encoding UTF8
    Write-Host "✅ Патч сохранен: claude_patches\$PatchName.patch" -ForegroundColor Green
    
    # Проверка валидности
    if ((.\claude_apply.ps1 check) -eq $true) {
        Write-Host "✅ Патч валиден" -ForegroundColor Green
    }
    else {
        Write-Host "❌ Есть проблемы с патчем" -ForegroundColor Red
    }
}

# Функция для открытия VS Code с задачами
function vscode-tasks {
    code . 
    Write-Host "💡 Используйте Ctrl+Shift+P -> 'Tasks: Run Task' для доступа к задачам Claude" -ForegroundColor Cyan
}

# Настройка PowerShell для лучшей работы
$PSDefaultParameterValues['Out-Default:OutVariable'] = 'LastResult'

# Улучшенный prompt с информацией о Git и Pi
function prompt {
    $currentPath = $PWD.Path
    
    # Показать текущую папку
    Write-Host "[" -NoNewline -ForegroundColor DarkGray
    Write-Host (Split-Path $currentPath -Leaf) -NoNewline -ForegroundColor Cyan
    Write-Host "] " -NoNewline -ForegroundColor DarkGray
    
    # Git статус если в git репозитории
    if (Test-Path .git) {
        $gitBranch = git branch --show-current 2>$null
        if ($gitBranch) {
            Write-Host "($gitBranch) " -NoNewline -ForegroundColor Yellow
        }
    }
    
    # Индикатор Pi статуса (быстрая проверка)
    if ($currentPath -like "*bedrock-app*") {
        if (Test-NetConnection -ComputerName $BEDROCK_PI_HOST -Port 22 -WarningAction SilentlyContinue -InformationLevel Quiet).TcpTestSucceeded {
            Write-Host "🟢 " -NoNewline
        }
        else {
            Write-Host "🔴 " -NoNewline
        }
    }
    
    return "PS> "
}

# Автокомплит для наших функций
Register-ArgumentCompleter -CommandName cp-rollback -ParameterName n -ScriptBlock {
    param($commandName, $parameterName, $wordToComplete, $commandAst, $fakeBoundParameters)
    1..10 | Where-Object { $_ -like "$wordToComplete*" }
}

Write-Host "🚀 Bedrock App PowerShell Profile загружен!" -ForegroundColor Green
Write-Host "Используйте 'bedrock-help' для справки" -ForegroundColor Cyan