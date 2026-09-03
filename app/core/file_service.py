import os
from uuid import uuid4
from fastapi import HTTPException, UploadFile, status

UPLOAD_DIR = "media/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


class FileService:

    @staticmethod
    async def save_image(
        file: UploadFile, folder: str = "products"
    ) -> str:
        # Extension tekshirish
        extension = file.filename.split(".")[-1].lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Faqat quyidagi formatlar qabul qilinadi: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        # Fayl hajmini tekshirish
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fayl hajmi 5MB dan oshmasligi kerak",
            )

        # Papka mavjud bo'lmasa yaratish
        target_dir = os.path.join(UPLOAD_DIR, folder)
        os.makedirs(target_dir, exist_ok=True)

        # Noyob fayl nomi va saqlash
        filename = f"{uuid4().hex}.{extension}"
        file_path = os.path.join(target_dir, filename)

        with open(file_path, "wb") as f:
            f.write(contents)

        # URL manzilini qaytarish
        return f"/media/{folder}/{filename}"

