import click

from bitcash.keygen import generate_matching_address


@click.group(invoke_without_command=True)
def bitcash():
    pass


@bitcash.command()
@click.argument("prefix")
@click.option("--cores", "-c", default="all")
def gen(prefix, cores):
    click.echo(generate_matching_address(prefix, cores))
