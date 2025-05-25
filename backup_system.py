"""
Sistema de Backup Seguro con Dask y Algoritmos de Compresión Clásicos
Proyecto Final - Programación de Sistemas
"""

import os
import sys
import zipfile
import gzip
import bz2
import shutil
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor

# Bibliotecas para paralelismo y procesamiento
import dask
from dask import delayed, bag as db
from dask.distributed import Client, as_completed
import dask.array as da

# Bibliotecas para encriptación
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# Interfaz gráfica
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Configuración del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompressionAlgorithm:
    """Enumeración de algoritmos de compresión soportados."""
    ZIP = 'zip'
    GZIP = 'gzip'
    BZIP2 = 'bzip2'

class StorageOption:
    """Enumeración de opciones de almacenamiento."""
    LOCAL = 'local'
    REMOTE = 'remote'
    USB_FRAGMENTS = 'usb_fragments'

class BackupConfig:
    """Configuración del sistema de backup."""
    def __init__(self):
        self.source_folder: List[str] = []
        self.compression_algorithm: str = CompressionAlgorithm.ZIP
        self.encrypt: bool = False
        self.password: Optional[str] = None
        self.storage_option: str = StorageOption.LOCAL
        self.destination_path: str = ""
        self.fragment_size: int = 100
        self.backup_name: str = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

class EncryptionManager:
    """Manejador de encriptación y desencriptación de archivos."""

    @staticmethod
    def generate_key_from_password(password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
        """Genera una clave de encripotación a partir de una contraseña."""
        if salt is None:
            salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt

    @staticmethod
    def encrypt_file(file_path: str, password: str) -> str:
        """Encripta un archivo y retorna la ruta del archivo encriptado usando Fernet."""
        key, salt = EncryptionManager.generate_key_from_password(password)
        fernet = Fernet(key)

        encrypt_path = f"{file_path}.encrypted"

        with open(file_path, 'rb') as original_file:
            original_data = original_file.read()
        encrypted_data = fernet.encrypt(original_data)

        # Guarda el salt al inicio del archivo encriptado
        with open(encrypted_path, 'wb') as encrypted_file:
            encrypted_file.write(salt)
            encrypted_file.write(encrypted_data)

        return encrypt_path

    @staticmethod
    def decrypt_file(encrypted_path: str, password: str, output_path: str):
        """Desencripta un archivo"""
        with open(encrypted_path, 'rb') as encrypted_file:
            salt = encrypted_file.read(16) # Los primeros 16 bytes son el salt
            encrypted_data = encrypted_file.read()

        key, _ = EncryptionManager.generate_key_from_password(password, salt)
        fernet = Fernet(key)

        original_data = fernet.decrypt(encrypted_data)

        with open(output_path, 'wb') as output_file:
            output_file.write(original_data)

class CompressionManager:
    """Maneja los algoritmos de compresión."""

    @staticmethod
    @delayed
    def compress_file_zip(source_folder: List[str], output_path: str) -> str:
        """Comprime múltiples carpetas usando ZIP con paralelismo Dask."""
        zip_path = f"{output_path}.zip"

        # Crea el archivo ZIP vacío
        with zipfile.ZipFile(output_path, 'w') as zf:
            pass

        # Recopila todos los archivos y carpetas usando Dask Bag
        all_files = []
        for folder in source_folder:
            folder_path = Path(folder)
            for file_path in folder_path.rglob('*'):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(folder_path.parent))

        # Procesa archivos en paralelo usando Dask
        file_bag = db.from_sequence(all_files)

        def add_to_zip(file_info):
            file_path, arcname = file_info
            try:
                # Usa un lock para escribir en el archivo ZIP de forma thread-safe
                with zipfile.ZipFile(zip_path, 'a', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                    zf.write(file_path, arcname)
                return f"Añadido: {arcname}"
            except Exception as e:
                return f"Error al añadir: {arcname} - {e}"

        # Procesar en paralelo
        results = file_bag.map(add_to_zip).compute()

        logger.info(f"Compresión ZIP completada. Resultados: {len(results)} archivos procesados.")
        return zip_path

    @staticmethod
    def compress_folder_gzip(source_folder: List[str], output_path: str) -> str:
        """Comprime múltiples carpetas usando GZIP (primero TAR, luego GZIP)."""
        import tarfile

        tar_path = f"{output_path}.tar"
        gzip_path = f"{output_path}.tar.gz"

        # Crea archivo TAR usando Dask para paralelismo
        with tarfile.open(tar_path, 'w') as tar:
            # Usar Dask para procesar carpetas en paralelo
            @delayed
            def add_folder_to_tar(folder):
                return folder
            
            folder_tasks = [add_folder_to_tar(folder) for folder in source_folders]
            processed_folders = dask.compute(*folder_tasks)

            for folder in processed_folders:
                folder_name = os.path.basename(folder)
                tar.add(folder, arcname=folder_name)

        # Comprime con GZIP
        with open(tar_path, 'rb') as f_in:
            with gzip.open(gzip_path, 'wb', compresslevel=6) as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Elimina el archivo TAR temporal
        os.remove(tar_path)

        logger.info(f"Compresión GZIP completada. Archivo: {gzip_path}")
        return gzip_path

    @staticmethod
    def compress_folder_bzip2(source_folder: List[str], output_path: str) -> str:
        """Comprime múltiples carpetas usando BZIP2 (primero TAR, luego BZIP2)."""
        import tarfile

        tar_path = f"{output_path}.tar"
        bzip2_path = f"{output_path}.tar.bz2"

        # Crea archivo TAR usando Dask para paralelismo
        with tarfile.open(tar_path, 'w') as tar:
            for folder in source_folder:
                folder_name = os.path.basename(folder)
                tar.add(folder, arcname=folder_name)
        
        # Comprime con BZIP2 usando paralelismo
        @delayed
        def compress_chunk(chunk_data):
            return bz2.compress(chunk_data, compresslevel=6)

        # Lee el archivo TAR y lo divide en fragmentos
        chunk_size = 1024 * 1024  # 1 MB
        with open(tar_path, 'rb') as f_in:
            with open(bzip2_path, 'wb') as f_out:
                chunks = []
                while True:
                    chunk = f_in.read(chunk_size)
                    if not chunk:
                        break
                    chunks.append(chunk)

                # Procesa los fragmentos en paralelo
                compressed_data = bz2.compress(b''.join(chunks), compresslevel=6)
                f_out.write(compressed_data)

        # Elimina el archivo TAR temporal
        os.remove(tar_path)

        logger.info(f"Compresión BZIP2 completada. Archivo: {bzip2_path}")
        return bzip2_path

class StorageManager:
    """Maneja las opciones de almacenamiento."""

    @staticmethod
    @delayed
    def copy_to_external_drive(source: str, destination_path: str):
        """Copia el archivo a un disco externo."""
        try:
            shutil.copy2(source, destination_path)
            return f"Archivo copiado a {destination_path}"
        except Exception as e:
            logger.error(f"Error al copiar a {destination_path}: {e}")
            return f"Error al copiar a {destination}: {e}"

    @staticmethod
    def fragment_file(file_path: str, fragment_size_mb: int, output_dir: str) -> List[str]:
        """Fragmenta un archivo en partes usando Dask"""
        fragment_size = fragment_size_mb * 1024 * 1024
        file_size = os.path.getsize(file_path)
        num_fragments = (file_size + fragment_size - 1) // fragment_size

        fragment_paths = []

        @delayed
        def create_fragment(fragment_num, start_pos, size):
            fragment_path = os.path.join(output_dir, f"{os.path.basename(file_path)}.part{fragment_num:03d}")

            with open(file_path, 'rb') as f_in:
                source.seek(start_pos)
                data = source.read(size)

                with open(fragment_path, 'wb') as fragment:
                    fragment.write(data)

            return fragment_path

        # Crea tareas de fragmentación en paralelo
        fragment_tasks = []
        for i in range(num_fragments):
            start_pos = i * fragment_size
            actual_size = min(fragment_size, file_size - start_pos)

            task = create_fragment(i, start_pos, actual_size)
            fragment_tasks.append(task)

        # Ejecuta las tareas de fragmentación
        fragment_paths = dask.compute(*fragment_tasks)

        # Crea archivos de metadatos
        metadata = {
            'original_file': os.path.basename(file_path),
            'total_fragments': num_fragments,
            'fragment_size': fragment_size,
            'original_size': file_size,
            'fragments': [os.path.basename(path) for path in fragment_paths]
        }

        metadata_path = os.path.join(output_dir, f"{os.path.basename(file_path)}.metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Archivo fragmentado: {file_path} en {num_fragments} partes.")
        return list(fragment_paths) + [metadata_path]

class BackupSystem:
    """Sistema principal de backup."""

    def __init__(self):
        self.config = BackupConfig()
        self.dask_client = None

    def initialize_dask(self):
        """Inicializa el cliente Dask para paralelismo."""
        try: 
            self.dask_client = Client(processes=False, threads_per_worker=2, n_workers=4)
            logger.info(f"Cliente Dask inicializado: {self.dask_client}")
        except Exception as e:
            logger.warning(f"Error al inicializar Dask: {e}")
            self.dask_client = None

    def create_backup(self, config: BackupConfig) -> str:
        """Crea un backup completo segun la configuración."""
        self.config = config

        if self.dask_client is None:
            self.initialize_dask()

        try:
            # Paso 1: Comprime los archivos
            logger.info("Starting compression...")
            if config.compression_algorithm == CompressionAlgorithm.ZIP:
                compressed_path = CompressionManager.compress_folder_zip(
                    config.source_folders, 
                    os.path.join(config.destination_path, config.backup_name)
                )
            elif config.compression_algorithm == CompressionAlgorithm.GZIP:
                compressed_path = CompressionManager.compress_folder_gzip(
                    config.source_folders,
                    os.path.join(config.destination_path, config.backup_name)
                )
            else:  # BZIP2
                compressed_path = CompressionManager.compress_folder_bzip2(
                    config.source_folders,
                    os.path.join(config.destination_path, config.backup_name)
                )
            
            # Paso 2: Encriptar si es necesario
            final_path = compressed_path
            if config.encrypt and config.password:
                logger.info("Starting encryption...")
                final_path = EncryptionManager.encrypt_file(compressed_path, config.password)
                os.remove(compressed_path)  # Eliminar archivo sin encriptar
            
            # Paso 3: Gestionar almacenamiento
            if config.storage_option == StorageOption.USB_FRAGMENTS:
                logger.info("Fragmenting file...")
                fragment_dir = os.path.join(config.destination_path, f"{config.backup_name}_fragments")
                os.makedirs(fragment_dir, exist_ok=True)
                
                fragments = StorageManager.fragment_file(
                    final_path, 
                    config.fragment_size_mb, 
                    fragment_dir
                )
                
                # Eliminar archivo original después de fragmentar
                os.remove(final_path)
                logger.info(f"Backup completed. Fragments created in: {fragment_dir}")
                return fragment_dir
            
            logger.info(f"Backup completed: {final_path}")
            return final_path
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise e

    def _restore_fragmented_backup(self, fragment_dir: str, metadata_file: str, destination: str, password: str = None):
        """Restaura un backup fragmentado"""
        # Leer metadatos
        with open(os.path.join(fragment_dir, metadata_file), 'r') as f:
            metadata = json.load(f)
        
        # Reconstruir archivo original
        reconstructed_path = os.path.join(destination, metadata['original_file'])
        
        with open(reconstructed_path, 'wb') as output:
            for fragment_name in metadata['fragments']:
                fragment_path = os.path.join(fragment_dir, fragment_name)
                with open(fragment_path, 'rb') as fragment:
                    output.write(fragment.read())

        # Continua con restauración normal
        return self._restore_normal_backup(reconstructed_path, destination, password)

    def _restore_normal_backup(self, backup_path: str, destination: str, password: str = None):
        """Restaura un backup normal"""
        current_path = backup_path

        # Desencripta si es necesario
        if backup_path.endswith('.encrypted') and password:
            decrypted_path = backup_path.replace('.encrypted', '')
            EncryptionManager.decrypt_file(backup_path, password, decrypted_path)
            current_path = decrypted_path

        # Descomprime el archivo
        if current_path.endswith('.zip'):
            with zipfile.ZipFile(current_path, 'r') as zf:
                zf.extractall(destination)
        elif current_path.endswith('.tar.gz'):
            import tarfile
            with tarfile.open(current_path, 'r:gz') as tar:
                tar.extractall(destination)
        elif current_path.endswith('.tar.bz2'):
            import tarfile
            with tarfile.open(current_path, 'r:bz2') as tar:
                tar.extractall(destination)

        logger.info(f"Backup restaurado en: {destination}")
        return destination

    def close(self):
        """Cierra el cliente Dask"""
        if self.dask_client:
            self.dask_client.close()

# Interfaz gráfica simple (IA)
class BackupGUI:
    """Interfaz gráfica del sistema de backup"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sistema de Backup Seguro")
        self.root.geometry("600x500")
        
        self.backup_system = BackupSystem()
        self.config = BackupConfig()
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Selección de carpetas
        ttk.Label(main_frame, text="Carpetas a respaldar:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        folder_frame = ttk.Frame(main_frame)
        folder_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.folder_listbox = tk.Listbox(folder_frame, height=4)
        self.folder_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        folder_scrollbar = ttk.Scrollbar(folder_frame, orient=tk.VERTICAL, command=self.folder_listbox.yview)
        folder_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.folder_listbox.configure(yscrollcommand=folder_scrollbar.set)
        
        ttk.Button(folder_frame, text="Agregar Carpeta", command=self.add_folder).grid(row=1, column=0, pady=5)
        
        # Opciones de compresión
        ttk.Label(main_frame, text="Algoritmo de compresión:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.compression_var = tk.StringVar(value=CompressionAlgorithm.ZIP)
        compression_frame = ttk.Frame(main_frame)
        compression_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Radiobutton(compression_frame, text="ZIP", variable=self.compression_var, value=CompressionAlgorithm.ZIP).grid(row=0, column=0)
        ttk.Radiobutton(compression_frame, text="GZIP", variable=self.compression_var, value=CompressionAlgorithm.GZIP).grid(row=0, column=1)
        ttk.Radiobutton(compression_frame, text="BZIP2", variable=self.compression_var, value=CompressionAlgorithm.BZIP2).grid(row=0, column=2)
        
        # Encriptación
        self.encrypt_var = tk.BooleanVar()
        ttk.Checkbutton(main_frame, text="Encriptar backup", variable=self.encrypt_var, command=self.toggle_encryption).grid(row=4, column=0, sticky=tk.W, pady=5)
        
        ttk.Label(main_frame, text="Contraseña:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.password_entry = ttk.Entry(main_frame, show="*", state="disabled")
        self.password_entry.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Destino
        ttk.Label(main_frame, text="Carpeta destino:").grid(row=6, column=0, sticky=tk.W, pady=5)
        dest_frame = ttk.Frame(main_frame)
        dest_frame.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.dest_var = tk.StringVar()
        ttk.Entry(dest_frame, textvariable=self.dest_var).grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(dest_frame, text="Seleccionar", command=self.select_destination).grid(row=0, column=1, padx=(5, 0))
        
        # Botones de acción
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=8, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Crear Backup", command=self.create_backup).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Restaurar Backup", command=self.restore_backup).grid(row=0, column=1, padx=5)
        
        # Barra de progreso
        self.progress = ttk.Progressbar(main_frame, length=400, mode='indeterminate')
        self.progress.grid(row=9, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))
        
        # Configurar peso de columnas
        main_frame.columnconfigure(1, weight=1)
        folder_frame.columnconfigure(0, weight=1)
        dest_frame.columnconfigure(0, weight=1)
    
    def add_folder(self):
        """Agrega una carpeta a la lista"""
        folder = filedialog.askdirectory()
        if folder:
            self.folder_listbox.insert(tk.END, folder)
    
    def toggle_encryption(self):
        """Habilita/deshabilita el campo de contraseña"""
        if self.encrypt_var.get():
            self.password_entry.configure(state="normal")
        else:
            self.password_entry.configure(state="disabled")
    
    def select_destination(self):
        """Selecciona la carpeta destino"""
        folder = filedialog.askdirectory()
        if folder:
            self.dest_var.set(folder)
    
    def create_backup(self):
        """Crea el backup"""
        try:
            # Validar entrada
            folders = list(self.folder_listbox.get(0, tk.END))
            if not folders:
                messagebox.showerror("Error", "Debe seleccionar al menos una carpeta")
                return
            
            if not self.dest_var.get():
                messagebox.showerror("Error", "Debe seleccionar una carpeta destino")
                return
            
            if self.encrypt_var.get() and not self.password_entry.get():
                messagebox.showerror("Error", "Debe ingresar una contraseña para encriptar")
                return
            
            # Configurar backup
            self.config.source_folders = folders
            self.config.compression_algorithm = self.compression_var.get()
            self.config.encrypt = self.encrypt_var.get()
            self.config.password = self.password_entry.get() if self.encrypt_var.get() else None
            self.config.destination_path = self.dest_var.get()
            
            # Mostrar progreso
            self.progress.start()
            
            # Crear backup en hilo separado
            import threading
            def backup_thread():
                try:
                    result = self.backup_system.create_backup(self.config)
                    self.root.after(0, lambda: self.backup_completed(result))
                except Exception as e:
                    self.root.after(0, lambda: self.backup_failed(str(e)))
            
            threading.Thread(target=backup_thread, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error creando backup: {e}")
    
    def backup_completed(self, result):
        """Callback cuando el backup se completa"""
        self.progress.stop()
        messagebox.showinfo("Éxito", f"Backup creado exitosamente:\n{result}")
    
    def backup_failed(self, error):
        """Callback cuando el backup falla"""
        self.progress.stop()
        messagebox.showerror("Error", f"Error creando backup:\n{error}")
    
    def restore_backup(self):
        """Restaura un backup"""
        backup_path = filedialog.askopenfilename(
            title="Seleccionar archivo de backup",
            filetypes=[
                ("Archivos comprimidos", "*.zip *.tar.gz *.tar.bz2"),
                ("Archivos encriptados", "*.encrypted"),
                ("Todos los archivos", "*.*")
            ]
        )
        
        if not backup_path:
            return
        
        dest_path = filedialog.askdirectory(title="Seleccionar carpeta de restauración")
        if not dest_path:
            return
        
        password = None
        if backup_path.endswith('.encrypted'):
            password = tk.simpledialog.askstring("Contraseña", "Ingrese la contraseña:", show='*')
            if not password:
                return
        
        try:
            self.progress.start()
            
            def restore_thread():
                try:
                    result = self.backup_system.restore_backup(backup_path, dest_path, password)
                    self.root.after(0, lambda: self.restore_completed(result))
                except Exception as e:
                    self.root.after(0, lambda: self.restore_failed(str(e)))
            
            import threading
            threading.Thread(target=restore_thread, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error restaurando backup: {e}")
    
    def restore_completed(self, result):
        """Callback cuando la restauración se completa"""
        self.progress.stop()
        messagebox.showinfo("Éxito", f"Backup restaurado exitosamente en:\n{result}")
    
    def restore_failed(self, error):
        """Callback cuando la restauración falla"""
        self.progress.stop()
        messagebox.showerror("Error", f"Error restaurando backup:\n{error}")
    
    def run(self):
        """Ejecuta la interfaz gráfica"""
        try:
            self.root.mainloop()
        finally:
            self.backup_system.close()

if __name__ == "__main__":
    # Crear y ejecutar la aplicación
    app = BackupGUI()
    app.run()