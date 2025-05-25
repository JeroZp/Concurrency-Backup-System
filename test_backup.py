#!/usr/bin/env python3
"""
Pruebas automatizadas para el Sistema de Backup Seguro
Incluye tests de funcionalidad, rendimiento y paralelismo
"""

import unittest
import os
import tempfile
import shutil
import time
import threading
from pathlib import Path
import zipfile
import json
import hashlib

# Importar nuestro sistema de backup
import sys
sys.path.append('.')

from backup_system import (
    BackupSystem, BackupConfig, CompressionAlgorithm, 
    StorageOption, CompressionManager, EncryptionManager, 
    StorageManager
)

class TestBackupSystem(unittest.TestCase):
    """Pruebas para el sistema de backup"""
    
    def setUp(self):
        """Configuración inicial para cada test"""
        self.test_dir = tempfile.mkdtemp()
        self.backup_system = BackupSystem()
        self.backup_system.initialize_dask()
        
        # Crear estructura de archivos de prueba
        self.create_test_files()
    
    def tearDown(self):
        """Limpieza después de cada test"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        if self.backup_system.dask_client:
            self.backup_system.close()
    
    def create_test_files(self):
        """Crea archivos de prueba con diferentes tamaños"""
        self.source_dir = os.path.join(self.test_dir, "source")
        os.makedirs(self.source_dir, exist_ok=True)
        
        # Crear archivos de diferentes tamaños
        test_files = {
            "small.txt": b"Contenido pequeño" * 100,  # ~1.7KB
            "medium.txt": b"Contenido mediano" * 10000,  # ~170KB
            "large.txt": b"Contenido grande" * 100000,  # ~1.7MB
        }
        
        for filename, content in test_files.items():
            with open(os.path.join(self.source_dir, filename), 'wb') as f:
                f.write(content)
        
        # Crear subdirectorio con más archivos
        subdir = os.path.join(self.source_dir, "subdir")
        os.makedirs(subdir, exist_ok=True)
        
        for i in range(5):
            with open(os.path.join(subdir, f"file_{i}.txt"), 'w') as f:
                f.write(f"Contenido del archivo {i}" * 1000)
    
    def test_zip_compression(self):
        """Prueba compresión ZIP"""
        print("\n=== Test: Compresión ZIP ===")
        
        config = BackupConfig()
        config.source_folders = [self.source_dir]
        config.compression_algorithm = CompressionAlgorithm.ZIP
        config.destination_path = self.test_dir
        config.backup_name = "test_zip"
        
        start_time = time.time()
        result = self.backup_system.create_backup(config)
        end_time = time.time()
        
        self.assertTrue(os.path.exists(result))
        self.assertTrue(result.endswith('.zip'))
        
        # Verificar que el archivo ZIP es válido
        with zipfile.ZipFile(result, 'r') as zf:
            files = zf.namelist()
            self.assertGreater(len(files), 0)
        
        print(f"ZIP compression completed in {end_time - start_time:.2f} seconds")
        print(f"Output file: {result}")
        print(f"Original size: {self._get_directory_size(self.source_dir)} bytes")
        print(f"Compressed size: {os.path.getsize(result)} bytes")
    
    def test_gzip_compression(self):
        """Prueba compresión GZIP"""
        print("\n=== Test: Compresión GZIP ===")
        
        config = BackupConfig()
        config.source_folders = [self.source_dir]
        config.compression_algorithm = CompressionAlgorithm.GZIP
        config.destination_path = self.test_dir
        config.backup_name = "test_gzip"
        
        start_time = time.time()
        result = self.backup_system.create_backup(config)
        end_time = time.time()
        
        self.assertTrue(os.path.exists(result))
        self.assertTrue(result.endswith('.tar.gz'))
        
        print(f"GZIP compression completed in {end_time - start_time:.2f} seconds")
        print(f"Output file: {result}")
        print(f"Compressed size: {os.path.getsize(result)} bytes")
    
    def test_bzip2_compression(self):
        """Prueba compresión BZIP2"""
        print("\n=== Test: Compresión BZIP2 ===")
        
        config = BackupConfig()
        config.source_folders = [self.source_dir]
        config.compression_algorithm = CompressionAlgorithm.BZIP2
        config.destination_path = self.test_dir
        config.backup_name = "test_bzip2"
        
        start_time = time.time()
        result = self.backup_system.create_backup(config)
        end_time = time.time()
        
        self.assertTrue(os.path.exists(result))
        self.assertTrue(result.endswith('.tar.bz2'))
        
        print(f"BZIP2 compression completed in {end_time - start_time:.2f} seconds")
        print(f"Output file: {result}")
        print(f"Compressed size: {os.path.getsize(result)} bytes")
    
    def test_encryption_decryption(self):
        """Prueba encriptación y desencriptación"""
        print("\n=== Test: Encriptación/Desencriptación ===")
        
        config = BackupConfig()
        config.source_folders = [self.source_dir]
        config.compression_algorithm = CompressionAlgorithm.ZIP
        config.encrypt = True
        config.password = "test_password_123"
        config.destination_path = self.test_dir
        config.backup_name = "test_encrypted"
        
        # Crear backup encriptado
        result = self.backup_system.create_backup(config)
        self.assertTrue(os.path.exists(result))
        self.assertTrue(result.endswith('.encrypted'))
        
        # Probar restauración
        restore_dir = os.path.join(self.test_dir, "restored")
        os.makedirs(restore_dir, exist_ok=True)
        
        self.backup_system.restore_backup(result, restore_dir, config.password)
        
        # Verificar que los archivos se restauraron correctamente
        restored_files = list(Path(restore_dir).rglob('*'))
        self.assertGreater(len(restored_files), 0)
        
        print(f"Encryption/Decryption test completed successfully")
        print(f"Encrypted file: {result}")
        print(f"Restored files: {len(restored_files)}")
    
    def test_file_fragmentation(self):
        """Prueba fragmentación de archivos"""
        print("\n=== Test: Fragmentación de Archivos ===")
        
        # Crear backup normal primero
        config = BackupConfig()
        config.source_folders = [self.source_dir]
        config.compression_algorithm = CompressionAlgorithm.ZIP
        config.destination_path = self.test_dir
        config.backup_name = "test_fragment"
        
        backup_path = self.backup_system.create_backup(config)
        
        # Fragmentar el archivo
        fragment_dir = os.path.join(self.test_dir, "fragments")
        os.makedirs(fragment_dir, exist_ok=True)
        
        fragments = StorageManager.fragment_file(backup_path, 1, fragment_dir)  # 1MB fragments
        
        self.assertGreater(len(fragments), 1)  # Debe haber al menos 2 archivos (fragmento + metadata)
        
        # Verificar que existe archivo de metadatos
        metadata_files = [f for f in fragments if f.endswith('.metadata.json')]
        self.assertEqual(len(metadata_files), 1)
        
        # Leer metadatos
        with open(metadata_files[0], 'r') as f:
            metadata = json.load(f)
        
        self.assertIn('total_fragments', metadata)
        self.assertIn('original_size', metadata)
        
        print(f"File fragmentation completed successfully")
        print(f"Original file size: {metadata['original_size']} bytes")
        print(f"Number of fragments: {metadata['total_fragments']}")
        print(f"Fragment files: {len(fragments)}")
    
    def test_compression_comparison(self):
        """Compara diferentes algoritmos de compresión"""
        print("\n=== Test: Comparación de Algoritmos ===")
        
        algorithms = [
            CompressionAlgorithm.ZIP,
            CompressionAlgorithm.GZIP,
            CompressionAlgorithm.BZIP2
        ]
        
        results = {}
        original_size = self._get_directory_size(self.source_dir)
        
        for algorithm in algorithms:
            config = BackupConfig()
            config.source_folders = [self.source_dir]
            config.compression_algorithm = algorithm
            config.destination_path = self.test_dir
            config.backup_name = f"test_comparison_{algorithm}"
            
            start_time = time.time()
            result = self.backup_system.create_backup(config)
            end_time = time.time()
            
            compressed_size = os.path.getsize(result)
            compression_ratio = (1 - compressed_size / original_size) * 100
            
            results[algorithm] = {
                'time': end_time - start_time,
                'size': compressed_size,
                'ratio': compression_ratio,
                'path': result
            }
        
        # Mostrar resultados
        print(f"\nOriginal size: {original_size:,} bytes")
        print("Algorithm | Time (s) | Size (bytes) | Compression Ratio")
        print("-" * 60)
        
        for alg, data in results.items():
            print(f"{alg:8} | {data['time']:7.2f} | {data['size']:11,} | {data['ratio']:13.1f}%")
    
    def test_parallel_performance(self):
        """Prueba el rendimiento del paralelismo con Dask"""
        print("\n=== Test: Rendimiento Paralelismo ===")
        
        # Crear más archivos para una prueba más significativa
        large_source_dir = os.path.join(self.test_dir, "large_source")
        os.makedirs(large_source_dir, exist_ok=True)
        
        # Crear 20 archivos de tamaño mediano
        for i in range(20):
            with open(os.path.join(large_source_dir, f"large_file_{i}.txt"), 'wb') as f:
                f.write(b"Contenido de prueba" * 50000)  # ~950KB cada archivo
        
        config = BackupConfig()
        config.source_folders = [large_source_dir]
        config.compression_algorithm = CompressionAlgorithm.ZIP
        config.destination_path = self.test_dir
        config.backup_name = "test_parallel"
        
        start_time = time.time()
        result = self.backup_system.create_backup(config)
        end_time = time.time()
        
        self.assertTrue(os.path.exists(result))
        
        total_size = self._get_directory_size(large_source_dir)
        processing_time = end_time - start_time
        throughput = total_size / processing_time / (1024 * 1024)  # MB/s
        
        print(f"Parallel processing completed successfully")
        print(f"Total data processed: {total_size / (1024*1024):.1f} MB")
        print(f"Processing time: {processing_time:.2f} seconds")
        print(f"Throughput: {throughput:.2f} MB/s")
        print(f"Dask client info: {self.backup_system.dask_client}")
    
    def test_restore_functionality(self):
        """Prueba completa de restauración"""
        print("\n=== Test: Funcionalidad de Restauración ===")
        
        # Crear backup
        config = BackupConfig()
        config.source_folders = [self.source_dir]
        config.compression_algorithm = CompressionAlgorithm.ZIP
        config.destination_path = self.test_dir
        config.backup_name = "test_restore"
        
        backup_path = self.backup_system.create_backup(config)
        
        # Restaurar backup
        restore_dir = os.path.join(self.test_dir, "restored")
        os.makedirs(restore_dir, exist_ok=True)
        
        self.backup_system.restore_backup(backup_path, restore_dir)
        
        # Verificar integridad comparando checksums
        original_files = self._get_file_checksums(self.source_dir)
        restored_files = self._get_file_checksums(restore_dir)
        
        # Comparar archivos (pueden estar en subdirectorios diferentes)
        original_basenames = {os.path.basename(k): v for k, v in original_files.items()}
        restored_basenames = {os.path.basename(k): v for k, v in restored_files.items()}
        
        common_files = set(original_basenames.keys()) & set(restored_basenames.keys())
        self.assertGreater(len(common_files), 0)
        
        # Verificar que los checksums coinciden
        for filename in common_files:
            if original_basenames[filename] != restored_basenames[filename]:
                self.fail(f"Checksum mismatch for file: {filename}")
        
        print(f"Restore functionality test completed successfully")
        print(f"Files verified: {len(common_files)}")
        print(f"Backup file: {backup_path}")
        print(f"Restored to: {restore_dir}")
    
    def _get_directory_size(self, directory):
        """Calcula el tamaño total de un directorio"""
        total = 0
        for path in Path(directory).rglob('*'):
            if path.is_file():
                total += path.stat().st_size
        return total
    
    def _get_file_checksums(self, directory):
        """Calcula checksums MD5 de todos los archivos en un directorio"""
        checksums = {}
        for path in Path(directory).rglob('*'):
            if path.is_file():
                with open(path, 'rb') as f:
                    content = f.read()
                    checksum = hashlib.md5(content).hexdigest()
                    checksums[str(path)] = checksum
        return checksums

class TestPerformanceMetrics(unittest.TestCase):
    """Pruebas específicas de rendimiento y métricas"""
    
    def setUp(self):
        """Configuración para pruebas de rendimiento"""
        self.test_dir = tempfile.mkdtemp()
        self.backup_system = BackupSystem()
        self.backup_system.initialize_dask()
    
    def tearDown(self):
        """Limpieza"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        if self.backup_system.dask_client:
            self.backup_system.close()
    
    def test_large_file_performance(self):
        """Prueba rendimiento con archivos grandes"""
        print("\n=== Test: Rendimiento con Archivos Grandes ===")
        
        # Crear archivo de ~10MB
        large_file_dir = os.path.join(self.test_dir, "large_files")
        os.makedirs(large_file_dir, exist_ok=True)
        
        large_file_path = os.path.join(large_file_dir, "large_file.txt")
        with open(large_file_path, 'wb') as f:
            # Escribir 10MB de datos
            for _ in range(1024):
                f.write(b"A" * 10240)  # 10KB por iteración
        
        file_size = os.path.getsize(large_file_path)
        print(f"Created test file: {file_size / (1024*1024):.1f} MB")
        
        # Probar diferentes algoritmos
        algorithms = [CompressionAlgorithm.ZIP, CompressionAlgorithm.GZIP, CompressionAlgorithm.BZIP2]
        
        for algorithm in algorithms:
            config = BackupConfig()
            config.source_folders = [large_file_dir]
            config.compression_algorithm = algorithm
            config.destination_path = self.test_dir
            config.backup_name = f"large_test_{algorithm}"
            
            start_time = time.time()
            result = self.backup_system.create_backup(config)
            end_time = time.time()
            
            compressed_size = os.path.getsize(result)
            compression_ratio = (1 - compressed_size / file_size) * 100
            speed = file_size / (end_time - start_time) / (1024 * 1024)  # MB/s
            
            print(f"{algorithm}: {end_time - start_time:.2f}s, "
                  f"{compression_ratio:.1f}% compression, "
                  f"{speed:.1f} MB/s")

def run_performance_benchmark():
    """Ejecuta un benchmark completo del sistema"""
    print("=" * 60)
    print("BENCHMARK COMPLETO DEL SISTEMA DE BACKUP")
    print("=" * 60)
    
    test_dir = tempfile.mkdtemp()
    backup_system = BackupSystem()
    
    try:
        backup_system.initialize_dask()
        
        # Crear datos de prueba de diferentes tamaños
        test_sizes = [
            ("small", 1),      # 1 MB
            ("medium", 10),    # 10 MB
            ("large", 100),    # 100 MB
        ]
        
        results = {}
        
        for size_name, size_mb in test_sizes:
            print(f"\n--- Testing with {size_name} dataset ({size_mb} MB) ---")
            
            # Crear datos de prueba
            source_dir = os.path.join(test_dir, f"source_{size_name}")
            os.makedirs(source_dir, exist_ok=True)
            
            # Crear archivos distribuidos
            num_files = max(1, size_mb // 2)  # Al menos 1 archivo, máximo size_mb/2
            file_size = (size_mb * 1024 * 1024) // num_files
            
            for i in range(num_files):
                with open(os.path.join(source_dir, f"file_{i}.dat"), 'wb') as f:
                    f.write(os.urandom(file_size))
            
            # Probar cada algoritmo
            size_results = {}
            
            for algorithm in [CompressionAlgorithm.ZIP, CompressionAlgorithm.GZIP, CompressionAlgorithm.BZIP2]:
                config = BackupConfig()
                config.source_folders = [source_dir]
                config.compression_algorithm = algorithm
                config.destination_path = test_dir
                config.backup_name = f"benchmark_{size_name}_{algorithm}"
                
                start_time = time.time()
                result_path = backup_system.create_backup(config)
                end_time = time.time()
                
                original_size = sum(os.path.getsize(os.path.join(source_dir, f)) 
                                  for f in os.listdir(source_dir))
                compressed_size = os.path.getsize(result_path)
                
                size_results[algorithm] = {
                    'time': end_time - start_time,
                    'original_size': original_size,
                    'compressed_size': compressed_size,
                    'compression_ratio': (1 - compressed_size / original_size) * 100,
                    'throughput': original_size / (end_time - start_time) / (1024 * 1024)
                }
                
                print(f"  {algorithm}: {end_time - start_time:.2f}s, "
                      f"{size_results[algorithm]['compression_ratio']:.1f}% compression, "
                      f"{size_results[algorithm]['throughput']:.1f} MB/s")
            
            results[size_name] = size_results
        
        # Generar reporte final
        print("\n" + "=" * 60)
        print("REPORTE FINAL DE RENDIMIENTO")
        print("=" * 60)
        
        for size_name, size_results in results.items():
            print(f"\n{size_name.upper()} DATASET:")
            print("Algorithm | Time (s) | Compression (%) | Throughput (MB/s)")
            print("-" * 55)
            for alg, data in size_results.items():
                print(f"{alg:8} | {data['time']:7.2f} | {data['compression_ratio']:13.1f} | {data['throughput']:13.1f}")
    
    finally:
        if backup_system.dask_client:
            backup_system.close()
        shutil.rmtree(test_dir, ignore_errors=True)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Sistema de pruebas para Backup Seguro")
    parser.add_argument("--benchmark", action="store_true", help="Ejecutar benchmark completo")
    parser.add_argument("--test", default="all", help="Ejecutar tests específicos (all, basic, performance)")
    
    args = parser.parse_args()
    
    if args.benchmark:
        run_performance_benchmark()
    else:
        # Configurar suite de tests
        if args.test == "all":
            suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
        elif args.test == "basic":
            suite = unittest.TestLoader().loadTestsFromTestCase(TestBackupSystem)
        elif args.test == "performance":
            suite = unittest.TestLoader().loadTestsFromTestCase(TestPerformanceMetrics)
        else:
            print(f"Test suite '{args.test}' no reconocido. Opciones: all, basic, performance")
            sys.exit(1)
        
        # Ejecutar tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        # Salir con código de error si hay fallos
        if not result.wasSuccessful():
            sys.exit(1)