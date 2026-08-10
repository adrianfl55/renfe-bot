# renfe-bot

[![CI](https://github.com/emartinez-dev/renfe-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/emartinez-dev/renfe-bot/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-%3E%3D%203.12-blue.svg)](https://www.python.org/)
[![Package Manager](https://img.shields.io/badge/package%20manager-uv-purple.svg)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Bot de Telegram y CLI para monitorizar la disponibilidad de billetes de tren en Renfe y recibir notificaciones push en el móvil en cuanto se libere un asiento.

---

## ⚡ Funcionalidades Principales

- 🤖 **Bot interactivo de Telegram**: Configuración fácil de búsquedas mediante `/buscar`.
- 🚉 **Búsqueda flexible**: Origen, destino y fechas de ida/vuelta con soporte de fecha en lenguaje natural.
- 🕒 **Filtros avanzados**: Filtrado por precio máximo, duración y hora máxima de salida.
- 💻 **CLI ligero**: Búsquedas rápidas y puntuales desde la consola (`uv run python src/cli.py`).
- 🐳 **Despliegue 24/7**: Listo para Docker y Docker Compose en segundo plano.

---

## 🚀 Inicio Rápido

### Opción 1: Con Docker Compose (Recomendado para servidores 24/7)

1. Crea tu archivo `.env` a partir de `.env.example`:
   ```bash
   cp .env.example .env
   ```
2. Pon tu token de Telegram obtenido de `@BotFather`:
   ```env
   TELEGRAM_TOKEN=123456789:ABCdefGhIjKlmNopQrsTuvWxYz
   ```
3. Ejecuta el contenedor en segundo plano:
   ```bash
   docker compose up -d --build
   ```

---

### Opción 2: Ejecución local con `uv`

1. Crea el entorno virtual e instala las dependencias con `uv`:
   ```bash
   uv venv
   uv pip install -r requirements.txt
   ```
2. Inicia el bot:
   ```bash
   # En Linux/macOS
   PYTHONPATH=src/ uv run python src/bot.py

   # En Windows PowerShell
   $env:PYTHONPATH="src"; uv run python src/bot.py
   ```
3. Ejecutar los tests:
   ```bash
   uv run pytest
   ```

---

## 📱 Uso desde Telegram

1. Envía el comando `/buscar` a tu bot en Telegram.
2. Indica Origen, Destino y Fecha/Hora a partir de la cual buscar.
3. Si activas los filtros, podrás establecer una **hora máxima de salida** (ej. salida `14:30` y límite `14:35`) para rastrear únicamente un tren específico.
4. El bot enviará una notificación push a tu teléfono tan pronto como detecte una plaza disponible.

---

## 🛠️ Mejoras y Modificaciones en este Fork

Este fork extiende las capacidades del proyecto original con las siguientes mejoras y propósitos:

- 🎯 **Filtro de tren específico (`max_departure_time`)**: Se añadió un nuevo estado y validación en la máquina de estados del bot para poder limitar la hora máxima de salida. **Propósito:** Permitir monitorizar únicamente un tren en concreto (ej. el tren de las 14:30) e ignorar el resto de trenes del día.
- ⚡ **Ecosistema basado exclusivamente en `uv`**: Se eliminó el uso de `pip` en favor de `uv` en todo el proyecto (desarrollo local, Dockerfile con `ghcr.io/astral-sh/uv` y CI/CD con `astral-sh/setup-uv`). **Propósito:** Garantizar instalaciones ultrarrápidas y reproducibles.
- 🔑 **Configuración mediante `.env`**: Se actualizó la carga de configuración en `src/config.py` para dar prioridad a la variable de entorno `TELEGRAM_TOKEN` sobre el archivo plano `config.ini`. **Propósito:** Cumplir con las mejores prácticas de seguridad en Docker y evitar la exposición de tokens en repositorios.
- 🐳 **Soporte Docker Compose**: Se incluyó un `docker-compose.yml` e historial de variables de entorno `.env.example`. **Propósito:** Facilitar el despliegue desatendido 24/7 en servidores domésticos o VPS sin configuración interactiva.

---

## 📄 Licencia

Este proyecto está licenciado bajo los términos de la licencia [MIT](LICENSE).
