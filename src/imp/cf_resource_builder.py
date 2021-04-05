import json
import troposphere.fis as fis
import troposphere.ssm as ssm
from troposphere import Sub
from constants import *
from resource_names import *


def build_ssm_document(template_name, name, ssm_content):
    doc = ssm.Document(ssm_document_name(template_name, name, True))

    doc.DocumentType = "Command"
    doc.Name = ssm_document_name(template_name, name, False)
    doc.Content = ssm_content

    return doc


def build_fis_template(template_name, role_arn, targets, actions, ssm_docs):
    doc = fis.ExperimentTemplate(
        fis_template_name(template_name, True),
        DependsOn=list(map(lambda d: ssm_document_name(template_name, d, True), ssm_docs))
    )

    # the API, at the very least, expects an empty stop condition
    none_stop_condition = fis.ExperimentTemplateStopCondition("StopCondition")
    none_stop_condition.Source = "none"

    doc.Description = "Template generated by Imp CLI."
    doc.RoleArn = role_arn
    doc.Actions = {
        fis_action_name(t['name']): build_fis_action(template_name, t) for t in actions if "name" in t
    }
    doc.StopConditions = [none_stop_condition]
    doc.Tags = {
        "Name": fis_template_name(template_name, False)
    }
    doc.Targets = {
        fis_target_name(template_name, t['name']):
            build_fis_target(t) for t in targets if "name" in t
    }

    return doc


def build_fis_target(target):
    fis_target = {}

    if "resource_type" in target:
        fis_target["ResourceType"] = target["resource_type"]

    if "selection_mode" in target:
        fis_target["SelectionMode"] = target["selection_mode"]

    if "resource_tags" in target:
        fis_target["ResourceTags"] = {
            t["key"]: t["value"] for t in target["resource_tags"]
        }

    return fis_target


def build_fis_action(template_name, action):
    fis_action = {}

    if action["type"] == ACTION_TYPE_IMP_RUN_SCRIPT:
        ssm_doc_arn = Sub(
            "arn:${AWS::Partition}:ssm:${AWS::Region}:${AWS::AccountId}:document/"
            + ssm_document_name(template_name, action["name"], False)
        )

        fis_action["ActionId"] = "aws:ssm:send-command"

        fis_action["Targets"] = {
            "Instances": fis_target_name(template_name, action["target"])
        }

        fis_action["Parameters"] = {
            "documentArn": ssm_doc_arn,
            "documentParameters": json.dumps(
                {
                    p["key"]: p["value"] for p in action["parameters"]
                }
            ),
            "duration": action["duration"]
        }

    return fis_action
