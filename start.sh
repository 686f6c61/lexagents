#!/bin/bash

################################################################################
# LexAgents - Script de Gestión Completo
#
# Funciones:
# - Instalación automática de dependencias
# - Creación de entornos virtuales
# - Detección y cambio de puertos
# - Arranque/parada del sistema
# - Verificación de salud
################################################################################

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuración por defecto
BACKEND_PORT=8000
FRONTEND_PORT=3000  # Puerto configurado en vite.config.js
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
LOGS_DIR="$PROJECT_DIR/logs"
VENV_DIR="$BACKEND_DIR/venv"
PID_FILE="$PROJECT_DIR/.lexagents.pid"

################################################################################
# FUNCIONES AUXILIARES
################################################################################

print_header() {
    echo ""
    echo -e "${CYAN}================================================================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}================================================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

################################################################################
# VERIFICACIÓN DE REQUISITOS
################################################################################

check_requirements() {
    print_header "Verificando Requisitos del Sistema"

    local all_ok=true

    # Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python encontrado: $PYTHON_VERSION"
    else
        print_error "Python 3 no encontrado. Instala Python 3.10 o superior"
        all_ok=false
    fi

    # Node.js
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_success "Node.js encontrado: $NODE_VERSION"
    else
        print_error "Node.js no encontrado. Instala Node.js 16 o superior"
        all_ok=false
    fi

    # npm
    if command -v npm &> /dev/null; then
        NPM_VERSION=$(npm --version)
        print_success "npm encontrado: v$NPM_VERSION"
    else
        print_error "npm no encontrado"
        all_ok=false
    fi

    # pip
    if python3 -m pip --version &> /dev/null; then
        print_success "pip encontrado"
    else
        print_error "pip no encontrado"
        all_ok=false
    fi

    if [ "$all_ok" = false ]; then
        print_error "Faltan requisitos necesarios. Por favor, instálalos e intenta de nuevo."
        exit 1
    fi

    echo ""
}

################################################################################
# GESTIÓN DE PUERTOS
################################################################################

check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Puerto ocupado
    else
        return 1  # Puerto libre
    fi
}

find_free_port() {
    local start_port=$1
    local port=$start_port

    while check_port $port; do
        ((port++))
    done

    echo $port
}

kill_port() {
    local port=$1
    print_info "Liberando puerto $port..."

    local pids=$(lsof -ti:$port 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -9 2>/dev/null
        sleep 1
        print_success "Puerto $port liberado"
        return 0
    else
        print_info "Puerto $port ya está libre"
        return 1
    fi
}

configure_ports() {
    print_header "Configuración de Puertos"

    # Backend
    if check_port $BACKEND_PORT; then
        print_warning "Puerto backend $BACKEND_PORT está ocupado"
        echo -n "¿Quieres liberar el puerto? (s/n): "
        read -r response
        if [[ "$response" =~ ^[Ss]$ ]]; then
            kill_port $BACKEND_PORT
        else
            NEW_BACKEND_PORT=$(find_free_port $((BACKEND_PORT + 1)))
            print_info "Usando puerto alternativo: $NEW_BACKEND_PORT"
            BACKEND_PORT=$NEW_BACKEND_PORT
        fi
    else
        print_success "Puerto backend $BACKEND_PORT disponible"
    fi

    # Frontend
    if check_port $FRONTEND_PORT; then
        print_warning "Puerto frontend $FRONTEND_PORT está ocupado"
        echo -n "¿Quieres liberar el puerto? (s/n): "
        read -r response
        if [[ "$response" =~ ^[Ss]$ ]]; then
            kill_port $FRONTEND_PORT
        else
            NEW_FRONTEND_PORT=$(find_free_port $((FRONTEND_PORT + 1)))
            print_info "Usando puerto alternativo: $NEW_FRONTEND_PORT"
            FRONTEND_PORT=$NEW_FRONTEND_PORT
        fi
    else
        print_success "Puerto frontend $FRONTEND_PORT disponible"
    fi

    echo ""
}

################################################################################
# INSTALACIÓN DE BACKEND
################################################################################

install_backend() {
    print_header "Instalando Backend"

    cd "$BACKEND_DIR" || exit 1

    # Crear entorno virtual si no existe
    if [ ! -d "$VENV_DIR" ]; then
        print_info "Creando entorno virtual..."
        python3 -m venv venv

        if [ $? -ne 0 ]; then
            print_error "Error creando entorno virtual"
            exit 1
        fi

        print_success "Entorno virtual creado"
    else
        print_info "Entorno virtual ya existe"
    fi

    # Activar entorno virtual
    source "$VENV_DIR/bin/activate"

    # Actualizar pip
    print_info "Actualizando pip..."
    python -m pip install --upgrade pip -q

    # Instalar dependencias
    if [ -f "requirements.txt" ]; then
        print_info "Instalando dependencias de Python..."
        pip install -r requirements.txt -q

        if [ $? -ne 0 ]; then
            print_error "Error instalando dependencias de Python"
            exit 1
        fi

        print_success "Dependencias de Python instaladas"
    else
        print_error "requirements.txt no encontrado"
        exit 1
    fi

    # Configurar .env si no existe
    if [ ! -f "$BACKEND_DIR/.env" ]; then
        print_warning ".env no encontrado en backend"

        if [ -f "$BACKEND_DIR/.env.example" ]; then
            cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
            print_info ".env creado desde .env.example"
            print_warning "⚠️  IMPORTANTE: Edita backend/.env y añade tu GEMINI_API_KEY"
            echo ""
            echo -n "Presiona Enter para continuar después de configurar .env..."
            read -r
        else
            print_info "Creando .env básico..."
            cat > "$BACKEND_DIR/.env" << EOF
# Google Gemini API Key
GEMINI_API_KEY=tu_api_key_aqui

# Configuración del API
API_HOST=0.0.0.0
API_PORT=$BACKEND_PORT
EOF
            print_warning "⚠️  IMPORTANTE: Edita backend/.env y añade tu GEMINI_API_KEY"
            echo ""
            echo -n "Presiona Enter para continuar después de configurar .env..."
            read -r
        fi
    else
        print_success ".env ya existe en backend"
    fi

    # Crear directorios necesarios
    mkdir -p "$BACKEND_DIR/data/json"
    mkdir -p "$BACKEND_DIR/data/results"
    mkdir -p "$BACKEND_DIR/data/cache"
    mkdir -p "$BACKEND_DIR/data/uploads"
    mkdir -p "$LOGS_DIR"

    print_success "Backend instalado correctamente"
    echo ""
}

################################################################################
# INSTALACIÓN DE FRONTEND
################################################################################

install_frontend() {
    print_header "Instalando Frontend"

    cd "$FRONTEND_DIR" || exit 1

    # Instalar dependencias
    if [ -f "package.json" ]; then
        print_info "Instalando dependencias de Node.js..."

        # Limpiar instalación previa si existe
        rm -rf node_modules package-lock.json 2>/dev/null

        npm install

        if [ $? -ne 0 ]; then
            print_error "Error instalando dependencias de Node.js"
            exit 1
        fi

        print_success "Dependencias de Node.js instaladas"
    else
        print_error "package.json no encontrado"
        exit 1
    fi

    # Configurar .env si no existe
    if [ ! -f "$FRONTEND_DIR/.env" ]; then
        print_info "Creando .env para frontend..."
        cat > "$FRONTEND_DIR/.env" << EOF
VITE_API_URL=http://localhost:$BACKEND_PORT
EOF
        print_success ".env creado en frontend"
    else
        print_success ".env ya existe en frontend"

        # Actualizar puerto si cambió
        sed -i "s|VITE_API_URL=.*|VITE_API_URL=http://localhost:$BACKEND_PORT|g" "$FRONTEND_DIR/.env"
    fi

    print_success "Frontend instalado correctamente"
    echo ""
}

################################################################################
# ARRANQUE DEL SISTEMA
################################################################################

start_backend() {
    print_info "Iniciando backend en puerto $BACKEND_PORT..."

    cd "$BACKEND_DIR" || exit 1
    source "$VENV_DIR/bin/activate"

    # Iniciar backend en background
    nohup python -m api.main > "$LOGS_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!

    # Esperar a que el backend arranque
    sleep 3

    # Verificar que sigue corriendo
    if ps -p $BACKEND_PID > /dev/null; then
        print_success "Backend iniciado (PID: $BACKEND_PID)"
        echo $BACKEND_PID >> "$PID_FILE"

        # Verificar salud
        sleep 2
        if curl -s "http://localhost:$BACKEND_PORT/api/v1/health" > /dev/null 2>&1; then
            print_success "Backend respondiendo correctamente"
        else
            print_warning "Backend arrancado pero no responde aún (puede tardar unos segundos)"
        fi
    else
        print_error "Backend falló al iniciar. Revisa logs/backend.log"
        return 1
    fi
}

start_frontend() {
    print_info "Iniciando frontend en puerto $FRONTEND_PORT..."

    cd "$FRONTEND_DIR" || exit 1

    # Iniciar frontend en background
    PORT=$FRONTEND_PORT nohup npm run dev > "$LOGS_DIR/frontend.log" 2>&1 &
    FRONTEND_PID=$!

    # Esperar a que el frontend arranque
    sleep 5

    # Verificar que sigue corriendo
    if ps -p $FRONTEND_PID > /dev/null; then
        print_success "Frontend iniciado (PID: $FRONTEND_PID)"
        echo $FRONTEND_PID >> "$PID_FILE"
    else
        print_error "Frontend falló al iniciar. Revisa logs/frontend.log"
        return 1
    fi
}

start_system() {
    print_header "Iniciando LexAgents"

    # Verificar si ya está corriendo
    if [ -f "$PID_FILE" ]; then
        print_warning "El sistema parece estar corriendo. Usa 'stop' primero."
        return 1
    fi

    # Crear carpeta logs
    mkdir -p "$LOGS_DIR"

    # Crear archivo PID
    touch "$PID_FILE"

    # Iniciar backend
    start_backend
    if [ $? -ne 0 ]; then
        rm "$PID_FILE"
        return 1
    fi

    # Iniciar frontend
    start_frontend
    if [ $? -ne 0 ]; then
        stop_system
        return 1
    fi

    echo ""
    print_success "=========================================="
    print_success "  Sistema iniciado correctamente"
    print_success "=========================================="
    echo ""
    print_info "🔌 Backend API: http://localhost:$BACKEND_PORT"
    print_info "📚 API Docs:    http://localhost:$BACKEND_PORT/docs"
    print_info "🌐 Frontend:    http://localhost:$FRONTEND_PORT"
    echo ""
    print_info "📝 Logs:"
    print_info "   Backend:  tail -f $LOGS_DIR/backend.log"
    print_info "   Frontend: tail -f $LOGS_DIR/frontend.log"
    print_info "   API:      tail -f $LOGS_DIR/api.log"
    echo ""
    print_info "Para detener: $0 stop"
    echo ""
}

################################################################################
# PARADA DEL SISTEMA
################################################################################

stop_system() {
    print_header "Deteniendo Sistema"

    if [ ! -f "$PID_FILE" ]; then
        print_warning "No se encontró archivo PID. ¿El sistema está corriendo?"

        # Intentar matar por puerto
        print_info "Intentando detener por puertos..."
        kill_port $BACKEND_PORT
        kill_port $FRONTEND_PORT
        return 0
    fi

    # Leer PIDs y matar procesos
    while read -r pid; do
        if ps -p $pid > /dev/null 2>&1; then
            print_info "Deteniendo proceso $pid..."
            kill $pid 2>/dev/null

            # Esperar a que termine
            sleep 2

            # Force kill si sigue vivo
            if ps -p $pid > /dev/null 2>&1; then
                kill -9 $pid 2>/dev/null
            fi

            print_success "Proceso $pid detenido"
        fi
    done < "$PID_FILE"

    # Limpiar archivo PID
    rm "$PID_FILE"

    # Asegurar que los puertos estén libres
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT

    print_success "Sistema detenido"
    echo ""
}

################################################################################
# ESTADO DEL SISTEMA
################################################################################

check_status() {
    print_header "Estado del Sistema"

    local backend_running=false
    local frontend_running=false

    # Verificar backend
    if check_port $BACKEND_PORT; then
        print_success "Backend: CORRIENDO (puerto $BACKEND_PORT)"
        backend_running=true

        # Verificar salud
        if curl -s "http://localhost:$BACKEND_PORT/api/v1/health" > /dev/null 2>&1; then
            print_success "  └─ API respondiendo correctamente"
        else
            print_warning "  └─ API no responde (puede estar iniciando)"
        fi
    else
        print_error "Backend: DETENIDO"
    fi

    # Verificar frontend
    if check_port $FRONTEND_PORT; then
        print_success "Frontend: CORRIENDO (puerto $FRONTEND_PORT)"
        frontend_running=true
    else
        print_error "Frontend: DETENIDO"
    fi

    echo ""

    if [ "$backend_running" = true ] && [ "$frontend_running" = true ]; then
        print_success "Sistema funcionando correctamente"
        echo ""
        print_info "🌐 Accede a: http://localhost:$FRONTEND_PORT"
    elif [ "$backend_running" = true ] || [ "$frontend_running" = true ]; then
        print_warning "Sistema parcialmente operativo"
    else
        print_error "Sistema detenido"
    fi

    echo ""
}

################################################################################
# LOGS
################################################################################

show_logs() {
    print_header "Logs del Sistema"

    echo "¿Qué logs quieres ver?"
    echo "1) Backend"
    echo "2) Frontend"
    echo "3) API"
    echo "4) Todos"
    echo ""
    echo -n "Selecciona (1-4): "
    read -r choice

    case $choice in
        1)
            if [ -f "$LOGS_DIR/backend.log" ]; then
                print_info "Mostrando logs del backend (Ctrl+C para salir)..."
                tail -f "$LOGS_DIR/backend.log"
            else
                print_error "No se encontró backend.log"
            fi
            ;;
        2)
            if [ -f "$LOGS_DIR/frontend.log" ]; then
                print_info "Mostrando logs del frontend (Ctrl+C para salir)..."
                tail -f "$LOGS_DIR/frontend.log"
            else
                print_error "No se encontró frontend.log"
            fi
            ;;
        3)
            if [ -f "$LOGS_DIR/api.log" ]; then
                print_info "Mostrando logs de la API (Ctrl+C para salir)..."
                tail -f "$LOGS_DIR/api.log"
            else
                print_error "No se encontró api.log"
            fi
            ;;
        4|*)
            print_info "Mostrando todos los logs (Ctrl+C para salir)..."
            tail -f "$LOGS_DIR"/*.log 2>/dev/null || print_error "No se encontraron archivos de log"
            ;;
    esac
}

################################################################################
# LIMPIEZA
################################################################################

clean_system() {
    print_header "Limpieza del Sistema"

    echo "¿Qué deseas limpiar?"
    echo "1) Logs"
    echo "2) Cache"
    echo "3) Resultados"
    echo "4) Todo lo anterior"
    echo "5) Cancelar"
    echo ""
    echo -n "Selecciona opción (1-5): "
    read -r choice

    case $choice in
        1)
            rm -f "$LOGS_DIR"/*.log
            print_success "Logs eliminados"
            ;;
        2)
            rm -rf "$BACKEND_DIR/data/cache"/*
            mkdir -p "$BACKEND_DIR/data/cache"
            print_success "Cache limpiado"
            ;;
        3)
            rm -rf "$BACKEND_DIR/data/results"/*
            mkdir -p "$BACKEND_DIR/data/results"
            print_success "Resultados eliminados"
            ;;
        4)
            rm -f "$LOGS_DIR"/*.log
            rm -rf "$BACKEND_DIR/data/cache"/*
            rm -rf "$BACKEND_DIR/data/results"/*
            mkdir -p "$BACKEND_DIR/data/cache"
            mkdir -p "$BACKEND_DIR/data/results"
            print_success "Sistema limpiado completamente"
            ;;
        5|*)
            print_info "Limpieza cancelada"
            ;;
    esac

    echo ""
}

################################################################################
# TESTS
################################################################################

run_tests() {
    print_header "Ejecutando Tests"

    cd "$BACKEND_DIR" || exit 1
    source "$VENV_DIR/bin/activate"

    if [ -f "run_tests.sh" ]; then
        chmod +x run_tests.sh
        ./run_tests.sh
    else
        print_error "run_tests.sh no encontrado"
        exit 1
    fi
}

################################################################################
# MENÚ PRINCIPAL
################################################################################

show_menu() {
    clear
    echo -e "${CYAN}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ██████╗ ██████╗  ██████╗ ██╗   ██╗███████╗███████╗████████╗ ║
║  ██╔═══██╗██╔══██╗██╔═══██╗██║   ██║██╔════╝██╔════╝╚══██╔══╝ ║
║  ██║   ██║██████╔╝██║   ██║██║   ██║█████╗  ███████╗   ██║    ║
║  ██║   ██║██╔══██╗██║▄▄ ██║██║   ██║██╔══╝  ╚════██║   ██║    ║
║  ╚██████╔╝██║  ██║╚██████╔╝╚██████╔╝███████╗███████║   ██║    ║
║   ╚═════╝ ╚═╝  ╚═╝ ╚══▀▀═╝  ╚═════╝ ╚══════╝╚══════╝   ╚═╝    ║
║                                                               ║
║              LexAgents - BOE & EUR-Lex                       ║
║                     Versión 2.0.0                             ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    echo "Selecciona una opción:"
    echo ""
    echo "  1) Instalar dependencias"
    echo "  2) Configurar puertos"
    echo "  3) Iniciar sistema"
    echo "  4) Detener sistema"
    echo "  5) Reiniciar sistema"
    echo "  6) Ver estado"
    echo "  7) Ver logs"
    echo "  8) Ejecutar tests"
    echo "  9) Limpiar sistema"
    echo " 10) Verificar requisitos"
    echo "  0) Salir"
    echo ""
    echo -n "Opción: "
}

main_menu() {
    while true; do
        show_menu
        read -r option

        case $option in
            1)
                check_requirements
                configure_ports
                install_backend
                install_frontend
                echo -n "Presiona Enter para continuar..."
                read -r
                ;;
            2)
                configure_ports
                echo -n "Presiona Enter para continuar..."
                read -r
                ;;
            3)
                start_system
                echo -n "Presiona Enter para continuar..."
                read -r
                ;;
            4)
                stop_system
                echo -n "Presiona Enter para continuar..."
                read -r
                ;;
            5)
                stop_system
                sleep 2
                start_system
                echo -n "Presiona Enter para continuar..."
                read -r
                ;;
            6)
                check_status
                echo -n "Presiona Enter para continuar..."
                read -r
                ;;
            7)
                show_logs
                ;;
            8)
                run_tests
                echo -n "Presiona Enter para continuar..."
                read -r
                ;;
            9)
                clean_system
                echo -n "Presiona Enter para continuar..."
                read -r
                ;;
            10)
                check_requirements
                echo -n "Presiona Enter para continuar..."
                read -r
                ;;
            0)
                print_info "¡Hasta luego!"
                exit 0
                ;;
            *)
                print_error "Opción inválida"
                sleep 1
                ;;
        esac
    done
}

################################################################################
# EJECUCIÓN PRINCIPAL
################################################################################

# Modo comando directo (sin menú)
if [ $# -gt 0 ]; then
    case "$1" in
        install)
            check_requirements
            configure_ports
            install_backend
            install_frontend
            ;;
        start)
            configure_ports
            start_system
            ;;
        stop)
            stop_system
            ;;
        restart)
            stop_system
            sleep 2
            start_system
            ;;
        status)
            check_status
            ;;
        logs)
            show_logs
            ;;
        test)
            run_tests
            ;;
        clean)
            clean_system
            ;;
        check)
            check_requirements
            ;;
        *)
            echo "Uso: $0 {install|start|stop|restart|status|logs|test|clean|check}"
            echo ""
            echo "O ejecuta sin argumentos para el menú interactivo:"
            echo "  $0"
            exit 1
            ;;
    esac
else
    # Modo menú interactivo
    main_menu
fi
