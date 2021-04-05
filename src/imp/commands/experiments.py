from cli_output import experiment_output
from clients.fis import *
from imp_template import *


@click.group()
@click.pass_context
def experiments(ctx):
    pass


@experiments.command()
@click.pass_context
@click.argument('template_name', type=click.STRING)
def list(ctx, template_name):
    for experiment in reversed(Fis().list(template_name)):
        experiment_output(experiment)


@experiments.command()
@click.pass_context
@click.argument('id', type=click.STRING)
def get_by_id(ctx, id):
    click.echo(Fis().get_by_id(id))


@experiments.command()
@click.pass_context
@click.argument('name', type=click.STRING)
def get(ctx, name):
    experiment_output(Fis().get_latest_by_name(name))


@experiments.command()
@click.pass_context
@click.option('--template', '-t', type=click.STRING, required=True)
@click.argument('name', type=click.STRING)
def start(ctx, template, name):
    click.echo(Fis().start(template, name))