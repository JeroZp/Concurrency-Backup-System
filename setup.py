#!/usr/bin/env python3
"""
Script de configuración e instalación para el Sistema de Backup Seguro
Automatiza la instalación de dependencias y configuración inicial
"""

import os
import sys
import subprocess
import platform
import tempfile
import shutil
from pathlib import Path

def check_python_version():
    """Verifica que la versión de Python sea compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Error: Se requiere Python 3.8 o superior")
        print(f"   Versión actual: Python {version.major}.{version.minor}.{version.micro}")
        print("   Por favor actualiza Python desde https://python.org")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detectado")
    return True

def check_system_requirements():
    """Verifica los requisitos del sistema"""
    print("\n🔍 Verificando requisitos del sistema...")
    
    # Verificar sistema operativo
    os_name = platform.system()
    supported_os = ["Windows", "Linux", "Darwin"]  # Darwin = macOS
    
    if os_name not in supported_os:
        print(f"⚠️  Advertencia: Sistema operativo '{os_name}' no oficialmente soportado")
        print("   El sistema puede funcionar pero no ha sido probado")
    else:
        print(f"✅ Sistema operativo soportado: {os_name}")
    
    # Verificar memoria RAM (aproximada)
    try:
        import psutil
        memory_gb = psutil.virtual_memory().total / (1024**3)
        if memory_gb < 4:
            print(f"⚠️  Advertencia: RAM detectada: {memory_gb:.1f}GB")
            print("   Se recomienda al menos 4GB RAM para funcionamiento óptimo")
        else:
            print(f"✅ RAM disponible: {memory_gb:.1f}GB")
    except ImportError:
        print("ℹ️  No se pudo verificar la RAM (psutil no disponible)")
    
    return True

def create_virtual_environment():
    """Crea un entorno virtual para el proyecto"""
    print("\n🐍 Configurando entorno virtual...")
    
    venv_path = Path("venv")
    
    if venv_path.exists():
        response = input("📁 El entorno virtual ya existe. ¿Recrear? (y/N): ")
        if response.lower() in ['y', 'yes', 'sí', 'si']:
            print("🗑️  Eliminando entorno virtual existente...")
            shutil.rmtree(venv_path)
        else:
            print("ℹ️  Usando entorno virtual existente")
            return True
    
    try:
        print("📦 Creando entorno virtual...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Entorno virtual creado exitosamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creando entorno virtual: {e}")
        return False

def get_pip_executable():
    """Obtiene la ruta del ejecutable pip del entorno virtual"""
    if platform.system() == "Windows":
        return Path("venv") / "Scripts" / "pip.exe"
    else:
        return Path("venv") / "bin" / "pip"

def install_dependencies():
    """Instala las dependencias del proyecto"""
    print("\n📚 Instalando dependencias...")
    
    pip_path = get_pip_executable()
    
    if not pip_path.exists():
        print("❌ Error: No se encontró pip en el entorno virtual")
        return False
    
    try:
        # Actualizar pip primero
        print("🔄 Actualizando pip...")
        subprocess.run([str(pip_path), "install", "--upgrade", "pip"], check=True)
        
        # Instalar dependencias principales
        dependencies = [
            "dask[complete]==2023.12.1",
            "distributed==2023.12.1", 
            "cryptography==3.0.0",
            "psutil==5.9.6"
        ]
        
        for dep in dependencies:
            print(f"📥 Instalando {dep}...")
            subprocess.run([str(pip_path), "install", dep], check=True)
        
        # Instalar dependencias opcionales
        print("📥 Instalando dependencias opcionales...")
        optional_deps = [
            "pytest==7.4.3",
            "pytest-cov==4.1.0",
            "colorlog==6.8.0"
        ]
        
        for dep in optional_deps:
            try:
                subprocess.run([str(pip_path), "install", dep], check=True)
            except subprocess.CalledProcessError:
                print(f"⚠️  No se pudo instalar dependencia opcional: {dep}")
        
        print("✅ Dependencias instaladas exitosamente")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando dependencias: {e}")
        return False

def create_project_structure():
    """Crea la estructura de directorios del proyecto"""
    print("\n📁 Creando estructura del proyecto...")
    
    directories = [
        "data",
        "backups", 
        "tests",
        "logs",
        "config"
    ]
    
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print(f"📂 Creado: {directory}/")
        else:
            print(f"📂 Existe: {directory}/")
    
    # Crear archivo de configuración por defecto
    config_file = Path("config") / "backup_config.json"
    if not config_file.exists():
        default_config = {
            "default_compression": "zip",
            "default_fragment_size_mb": 100,
            "max_workers": 4,
            "threads_per_worker": 2,
            "log_level": "INFO"
        }
        
        import json
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        print(f"⚙️  Creado archivo de configuración: {config_file}")
    
    print("✅ Estructura del proyecto configurada")

def run_tests():
    """Ejecuta las pruebas básicas del sistema"""
    print("\n🧪 Ejecutando pruebas básicas...")
    
    # Verificar que los archivos principales existen
    required_files = [
        "backup_system.py",
        "test_backup.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Archivos faltantes: {', '.join(missing_files)}")
        print("   Por favor asegúrate de tener todos los archivos del proyecto")
        return False
    
    # Ejecutar pruebas básicas de importación
    try:
        python_path = get_python_executable()
        print("🔍 Verificando importaciones...")
        
        test_script = """
import sys
sys.path.append('.')

try:
    from backup_system import BackupSystem, BackupConfig
    print("✅ Importación exitosa")
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    sys.exit(1)

try:
    import dask
    print(f"✅ Dask {dask.__version__} disponible")
except ImportError:
    print("❌ Dask no disponible")
    sys.exit(1)

try:
    from cryptography.fernet import Fernet
    print("✅ Cryptography disponible")
except ImportError:
    print("❌ Cryptography no disponible")
    sys.exit(1)
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            temp_script = f.name
        
        try:
            result = subprocess.run([str(python_path), temp_script], 
                                  capture_output=True, text=True, check=True)
            print(result.stdout)
            print("✅ Pruebas básicas completadas exitosamente")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Error en las pruebas: {e}")
            if e.stdout:
                print("STDOUT:", e.stdout)
            if e.stderr:
                print("STDERR:", e.stderr)
            return False
        finally:
            os.unlink(temp_script)
            
    except Exception as e:
        print(f"❌ Error ejecutando pruebas: {e}")
        return False

def get_python_executable():
    """Obtiene la ruta del ejecutable Python del entorno virtual"""
    if platform.system() == "Windows":
        return Path("venv") / "Scripts" / "python.exe"
    else:
        return Path("venv") / "bin" / "python"

def create_launch_scripts():
    """Crea scripts de lanzamiento para diferentes plataformas"""
    print("\n🚀 Creando scripts de lanzamiento...")
    
    # Script para Windows
    windows_script = """@echo off
echo Iniciando Sistema de Backup Seguro...
cd /d "%~dp0"
venv\\Scripts\\python.exe backup_system.py
if errorlevel 1 (
    echo.
    echo Error ejecutando el sistema de backup.
    echo Presiona cualquier tecla para continuar...
    pause >nul
)
"""
    
    with open("run_backup.bat", 'w') as f:
        f.write(windows_script)
    print("📝 Creado: run_backup.bat (Windows)")
    
    # Script para Unix/Linux/macOS
    unix_script = """#!/bin/bash
echo "Iniciando Sistema de Backup Seguro..."
cd "$(dirname "$0")"
venv/bin/python backup_system.py
if [ $? -ne 0 ]; then
    echo ""
    echo "Error ejecutando el sistema de backup."
    echo "Presiona Enter para continuar..."
    read
fi
"""
    
    with open("run_backup.sh", 'w') as f:
        f.write(unix_script)
    
    # Hacer ejecutable en Unix
    if platform.system() != "Windows":
        os.chmod("run_backup.sh", 0o755)
    
    print("📝 Creado: run_backup.sh (Unix/Linux/macOS)")
    
    # Script de pruebas
    test_script = """#!/bin/bash
echo "Ejecutando pruebas del Sistema de Backup..."
cd "$(dirname "$0")"
venv/bin/python test_backup.py --test basic
"""
    
    with open("run_tests.sh", 'w') as f:
        f.write(test_script)
    
    if platform.system() != "Windows":
        os.chmod("run_tests.sh", 0o755)
    
    print("📝 Creado: run_tests.sh")

def print_next_steps():
    """Muestra los siguientes pasos al usuario"""
    print("\n🎉 ¡Instalación completada exitosamente!")
    print("\n📋 Próximos pasos:")
    print("   1. Para ejecutar el sistema:")
    
    if platform.system() == "Windows":
        print("      • Doble clic en 'run_backup.bat', o")
        print("      • Ejecutar: venv\\Scripts\\python backup_system.py")
    else:
        print("      • Ejecutar: ./run_backup.sh, o")
        print("      • Ejecutar: venv/bin/python backup_system.py")
    
    print("\n   2. Para ejecutar pruebas:")
    print("      • ./run_tests.sh (Unix/Linux/macOS)")
    print("      • venv/bin/python test_backup.py --test basic")
    
    print("\n   3. Para ejecutar benchmark completo:")
    print("      • venv/bin/python test_backup.py --benchmark")
    
    print("\n📁 Estructura del proyecto:")
    print("   backup_system.py    - Aplicación principal")
    print("   test_backup.py      - Suite de pruebas")
    print("   requirements.txt    - Dependencias")
    print("   config/            - Archivos de configuración")
    print("   data/              - Datos de prueba")
    print("   backups/           - Backups generados")
    print("   logs/              - Archivos de log")
    
    print("\n💡 Consejos:")
    print("   • Revisa config/backup_config.json para ajustar configuraciones")
    print("   • Los logs se guardan automáticamente en logs/")
    print("   • Para desarrollo, usa el entorno virtual: source venv/bin/activate")
    
    print("\n🆘 Soporte:")
    print("   • Documentación: README.md y documentación técnica")
    print("   • Pruebas: Ejecuta tests antes de usar en producción")
    print("   • Logs: Revisa logs/ si hay problemas")

def main():
    """Función principal del script de configuración"""
    print("=" * 60)
    print("🛠️  INSTALADOR DEL SISTEMA DE BACKUP SEGURO")
    print("=" * 60)
    print("Este script configurará automáticamente el entorno para ejecutar")
    print("el Sistema de Backup Seguro con Dask y algoritmos de compresión clásicos.")
    print()
    
    # Verificar requisitos básicos
    if not check_python_version():
        sys.exit(1)
    
    if not check_system_requirements():
        print("⚠️  Continuando a pesar de las advertencias...")
    
    # Confirmar instalación
    response = input("\n🚀 ¿Continuar con la instalación? (Y/n): ")
    if response.lower() in ['n', 'no']:
        print("❌ Instalación cancelada por el usuario")
        sys.exit(0)
    
    # Ejecutar pasos de instalación
    steps = [
        ("Crear entorno virtual", create_virtual_environment),
        ("Instalar dependencias", install_dependencies),
        ("Configurar estructura", create_project_structure),
        ("Crear scripts de lanzamiento", create_launch_scripts),
        ("Ejecutar pruebas básicas", run_tests)
    ]
    
    failed_steps = []
    
    for step_name, step_function in steps:
        print(f"\n{'='*20} {step_name} {'='*20}")
        
        try:
            if not step_function():
                failed_steps.append(step_name)
                print(f"❌ Falló: {step_name}")
            else:
                print(f"✅ Completado: {step_name}")
        except Exception as e:
            print(f"❌ Error inesperado en {step_name}: {e}")
            failed_steps.append(step_name)
    
    # Mostrar resumen final
    print("\n" + "="*60)
    print("📊 RESUMEN DE INSTALACIÓN")
    print("="*60)
    
    if failed_steps:
        print("❌ Pasos que fallaron:")
        for step in failed_steps:
            print(f"   • {step}")
        print("\n⚠️  La instalación se completó con errores.")
        print("   Revisa los mensajes anteriores y ejecuta el script nuevamente.")
    else:
        print("✅ Todos los pasos completados exitosamente")
        print_next_steps()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Instalación interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error crítico durante la instalación: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
