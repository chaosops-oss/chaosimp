import humps
import troposphere.ssm as ssm
import troposphere.fis as fis
from troposphere import GetAtt, Ref, Join, Sub
from constants import *


def build_ssm_document(name, ssm_content):
    doc = ssm.Document(__ssm_document_name(name))

    doc.DocumentType = "Command"
    doc.Content = ssm_content

    return doc


def build_fis_template(name, role_arn, targets, actions, ssm_docs):
    doc = fis.ExperimentTemplate(
        __fis_template_name(name),
        DependsOn=list(map(lambda d: __ssm_document_name(d), ssm_docs))
    )

    # the API, at the very least, expects an empty stop condition
    none_stop_condition = fis.ExperimentTemplateStopCondition("StopCondition")
    none_stop_condition.Source = "none"

    doc.Description = "Template generated by Imp CLI."
    doc.RoleArn = role_arn
    doc.Actions = {
        humps.pascalize(f"fis-target-{t['name']}"): build_fis_action(t, ssm_docs) for t in actions if "name" in t
    }
    doc.StopConditions = [none_stop_condition]
    doc.Tags = {}
    doc.Targets = {
        humps.pascalize(__fis_target_name(t['name'])): build_fis_target(t) for t in targets if "name" in t
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


def build_fis_action(action, ssm_docs):
    fis_action = {}

    if action["type"] == ACTION_TYPE_IMP_RUN_SCRIPT:
        ssm_doc_arn = Sub(
            "arn:${AWS::Partition}:ssm:${AWS::Region}:${AWS::AccountId}:document/${DocumentName}",
            DocumentName=Ref(ssm_docs[action["name"]])
        )

        fis_action["ActionId"] = "aws:ssm:send-command"

        fis_action["Targets"] = {
            "Instances": __fis_target_name(action["target"])
        }


        fis_action["Parameters"] = {
            "documentArn": ssm_doc_arn,
            "duration": action["duration"]
        }

    return fis_action


def __ssm_document_name(name):
    return humps.pascalize(f"ssm-doc-{name}")


def __fis_template_name(name):
    return humps.pascalize(f"fis-template-{name}")


def __fis_target_name(name):
    return humps.pascalize(f"fis-target-{name}")
