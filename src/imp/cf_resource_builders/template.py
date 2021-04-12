import json
from typing import Dict, Any

import troposphere.fis as fis
import troposphere.ssm as ssm
from troposphere import Sub

from name_constants import *
from resource_names import *


def build_ssm_document(template_name: str, name: str, ssm_content: dict) -> ssm.Document:
    doc = ssm.Document(ssm_document_name(template_name, name, True))

    doc.DocumentType = "Command"
    doc.Name = ssm_document_name(template_name, name, False)
    doc.Content = ssm_content

    return doc


def build_fis_template(template_name: str, role_arn: str, data: dict, ssm_docs: list) -> fis.ExperimentTemplate:
    targets = data.get("Targets", [])
    actions = data.get("Actions", [])
    stop_conditions = data.get("StopConditions", [])

    doc = fis.ExperimentTemplate(
        fis_template_name(template_name, True),
        DependsOn=list(map(lambda d: ssm_document_name(template_name, d, True), ssm_docs))
    )

    if not stop_conditions:
        # the API, at the very least, expects an empty stop condition
        none_stop_condition = fis.ExperimentTemplateStopCondition("StopCondition")
        none_stop_condition.Source = "none"

        stop_conditions.append(none_stop_condition)

    doc.Description = "Template generated by Imp CLI."

    doc.RoleArn = role_arn

    doc.Targets = {
        fis_target_name(template_name, t.get("Name")): build_fis_target(t) for t in targets
    }

    doc.Actions = {
        fis_action_name(a.get("Name")): build_fis_action(template_name, a) for a in actions
    }

    doc.StopConditions = stop_conditions

    doc.Tags = {
        "Name": fis_template_name(template_name, False)
    }

    return doc


def build_fis_target(target: dict) -> dict:
    if "ResourceTags" in target:
        tags = target["ResourceTags"]

        target["ResourceTags"] = {
            t["Key"]: t["Value"] for t in tags
        }

    target.pop('Name', None)

    return target


def build_fis_action(template_name: str, action: dict) -> dict:
    fis_action: Dict[str, Any] = {
        "Parameters": {humps.camelize(k): v for k, v in action.get("Parameters", {}).items()},
        "Targets": {
            "Instances": fis_target_name(template_name, action["Target"])
        },
        "StartAfter": list(map(lambda a: fis_action_name(a), action.get("StartAfter", [])))
    }

    if action["Type"] == ACTION_TYPE_IMP_RUN_SCRIPT:
        fis_action["ActionId"] = "aws:ssm:send-command"

        ssm_doc_arn = Sub(
            "arn:${AWS::Partition}:ssm:${AWS::Region}:${AWS::AccountId}:document/"
            + ssm_document_name(template_name, action.get("Name"), False)
        )

        fis_action["Parameters"]["documentArn"] = ssm_doc_arn

        fis_action["Parameters"]["documentParameters"] = json.dumps(
            {
                p["Key"]: p["Value"] for p in action.get("Document", {}).get("Parameters", [])
            }
        )

        return fis_action
    else:
        fis_action["ActionId"] = action["Type"]

        return fis_action