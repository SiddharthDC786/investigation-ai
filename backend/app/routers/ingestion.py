from fastapi import APIRouter, UploadFile

router = APIRouter(prefix="/ingest", tags=["ingestion"])

@router.post("/cdr")
async def ingest_cdr(file: UploadFile):
    contents = await file.read()
    lines = contents.decode().splitlines()
    return {
        "status": "success",
        "source_id": "SRC001",
        "records_received": max(len(lines) - 1, 0)
    }

@router.post("/fir")
async def ingest_fir(file: UploadFile):
    contents = await file.read()
    return {
        "status": "success",
        "source_id": "SRC002",
        "characters_received": len(contents.decode())
    }

@router.post("/transactions")
async def ingest_transactions(file: UploadFile):
    contents = await file.read()
    lines = contents.decode().splitlines()
    return {
        "status": "success",
        "source_id": "SRC003",
        "records_received": max(len(lines) - 1, 0)
    }

@router.post("/surveillance")
async def ingest_surveillance(file: UploadFile):
    contents = await file.read()
    return {
        "status": "success",
        "source_id": "SRC004",
        "characters_received": len(contents.decode())
    }