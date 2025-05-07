from cryptography.fernet import Fernet
import os
import logging

def generate_encryption_key():
    """Генерирует новый ключ шифрования и сохраняет его в файл.

    Returns:
        bytes: Сгенерированный ключ шифрования.
    """
    key = Fernet.generate_key()
    with open("encryption_key.bin", "wb") as f:
        f.write(key)
    return key

def load_encryption_key():
    """Загружает существующий ключ шифрования или генерирует новый, если файл не существует.

    Returns:
        bytes: Ключ шифрования.
    """
    if os.path.exists("encryption_key.bin"):
        with open("encryption_key.bin", "rb") as f:
            return f.read()
    return generate_encryption_key()

def encrypt_api_key(api_key, encryption_key):
    """Шифрует API-ключ с использованием ключа шифрования.

    Args:
        api_key (str): API-ключ для шифрования.
        encryption_key (bytes): Ключ шифрования.

    Returns:
        bytes: Зашифрованный API-ключ.
    """
    fernet = Fernet(encryption_key)
    return fernet.encrypt(api_key.encode())

def decrypt_api_key(encrypted_key, encryption_key):
    """Расшифровывает API-ключ с использованием ключа шифрования.

    Args:
        encrypted_key (bytes): Зашифрованный API-ключ.
        encryption_key (bytes): Ключ шифрования.

    Returns:
        str: Расшифрованный API-ключ.
    """
    fernet = Fernet(encryption_key)
    return fernet.decrypt(encrypted_key).decode()

def save_api_key(api_key):
    """Сохраняет зашифрованный API-ключ в файл.

    Args:
        api_key (str): API-ключ для сохранения.

    Raises:
        Exception: Если произошла ошибка при сохранении.
    """
    try:
        encryption_key = load_encryption_key()
        encrypted_key = encrypt_api_key(api_key, encryption_key)
        with open("encrypted_api_key.bin", "wb") as f:
            f.write(encrypted_key)
        logging.info("API-ключ успешно сохранен")
    except Exception as e:
        logging.error(f"Ошибка сохранения API-ключа: {str(e)}")
        raise

def load_api_key():
    """Загружает и расшифровывает API-ключ из файла.

    Returns:
        str or None: Расшифрованный API-ключ или None, если файл не существует или произошла ошибка.
    """
    try:
        if not os.path.exists("encrypted_api_key.bin"):
            return None
        encryption_key = load_encryption_key()
        with open("encrypted_api_key.bin", "rb") as f:
            encrypted_key = f.read()
        return decrypt_api_key(encrypted_key, encryption_key)
    except Exception as e:
        logging.error(f"Ошибка загрузки API-ключа: {str(e)}")
        return None