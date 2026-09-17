from xml.etree import ElementTree as ET

from gtmdq.config import PROJECT_ROOT, read_yaml

NS = {"m": "http://soap.sforce.com/2006/04/metadata"}
BASE = PROJECT_ROOT / "force-app/main/default"


def test_all_declared_fields_exist_and_external_ids_are_unique():
    schema = read_yaml(PROJECT_ROOT / "config/salesforce_schema.yml")
    for obj, fields in schema["objects"].items():
        expected = fields if obj == "Data_Quality_Issue__c" else schema["common"] + fields
        paths = list((BASE / "objects" / obj / "fields").glob("*.field-meta.xml"))
        assert len(paths) == len(expected)
        for field in expected:
            root = ET.parse(BASE / "objects" / obj / "fields" / f"{field['name']}.field-meta.xml")
            assert root.findtext("m:fullName", namespaces=NS) == field["name"]
            assert root.findtext("m:type", namespaces=NS) == field["type"]
            if field.get("external"):
                assert root.findtext("m:externalId", namespaces=NS) == "true"
                assert root.findtext("m:unique", namespaces=NS) == "true"


def test_prevention_inactive_and_permissions_exclude_delete():
    paths = list((BASE / "objects").rglob("*.validationRule-meta.xml"))
    assert len(paths) == 3
    for path in paths:
        root = ET.parse(path)
        assert root.findtext("m:active", namespaces=NS) == "false"
    permissions = ET.parse(BASE / "permissionsets/GTMDQ_Operator.permissionset-meta.xml")
    for permission in permissions.findall("m:objectPermissions", NS):
        assert permission.findtext("m:allowDelete", namespaces=NS) == "false"
        assert permission.findtext("m:modifyAllRecords", namespaces=NS) == "false"
