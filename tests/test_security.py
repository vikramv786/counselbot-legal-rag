
import json
from pathlib import Path

from counselbot_legal_rag.security import can_access_document


DATASET_DIR = Path(__file__).resolve().parents[1] / "veridian_legal_dataset"

users = json.loads((DATASET_DIR / "users_seed.json").read_text())
documents = json.loads((DATASET_DIR / "manifest.json").read_text())


def get_user(username):
    return next(user for user in users if user["username"] == username)


def get_document(doc_id):
    return next(doc for doc in documents if doc["doc_id"] == doc_id)


def test_authorized_user():
    user = get_user("adv.rao")
    document = get_document("VLH-MTR-017")

    assert can_access_document(user, document) is True


def test_wrong_role():
    user = get_user("para.sneha")
    document = get_document("VLH-MTR-017")

    assert can_access_document(user, document) is False


def test_wrong_matter():
    user = get_user("adv.nair")
    document = get_document("VLH-MTR-017")

    assert can_access_document(user, document) is False


def test_general_document():
    user = get_user("comp.bose")
    document = get_document("VLH-GEN-001")

    assert can_access_document(user, document) is True


def test_general_counsel_all_matters():
    user = get_user("gc.sharma")
    document = get_document("VLH-MTR-044")

    assert can_access_document(user, document) is True


def test_cross_department_access_blocked():
    user = get_user("comp.bose")
    document = get_document("VLH-CON-001")

    assert can_access_document(user, document) is False
