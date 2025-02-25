#!/bin/bash

# Скрипт для запуска пошагового анализа рекламных кампаний
# Использование: ./campaign_analysis.sh [опции]
# Опции:
#   --year YEAR     - Год для фильтрации кампаний (по умолчанию 2025)
#   --days DAYS     - Количество дней для анализа (по умолчанию 14)
#   --no-cache      - Отключить использование кэша
#   --clear-cache   - Очистить кэш перед запуском

# Устанавливаем значения по умолчанию
YEAR="2025"
DAYS="14"
USE_CACHE=true
CLEAR_CACHE=false

# Парсим аргументы командной строки
while [[ $# -gt 0 ]]; do
  case $1 in
    --year)
      YEAR="$2"
      shift 2
      ;;
    --days)
      DAYS="$2"
      shift 2
      ;;
    --no-cache)
      USE_CACHE=false
      shift
      ;;
    --clear-cache)
      CLEAR_CACHE=true
      shift
      ;;
    *)
      echo "Неизвестный параметр: $1"
      exit 1
      ;;
  esac
done

# Путь к директории скрипта
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Запуск Python-скрипта с поддержкой прерывания Ctrl+C
echo "Запуск пошагового анализа рекламных кампаний..."
echo "Год: $YEAR, дней для анализа: $DAYS"
echo "Использование кэша: $USE_CACHE"
echo "Очистка кэша: $CLEAR_CACHE"
echo "---------------------------------------------------"

# Формируем параметры командной строки для Python-скрипта
PYTHON_ARGS=""

if [ "$USE_CACHE" = false ]; then
  PYTHON_ARGS="$PYTHON_ARGS --no-cache"
fi

if [ "$CLEAR_CACHE" = true ]; then
  PYTHON_ARGS="$PYTHON_ARGS --clear-cache"
fi

# Запуск скрипта
python "$SCRIPT_DIR/campaign_analyzer.py" --year "$YEAR" --days "$DAYS" $PYTHON_ARGS

# Проверка кода возврата
if [ $? -eq 0 ]; then
  echo "Анализ успешно завершен."
else
  echo "Ошибка при выполнении анализа. Проверьте журнал логов."
fi 