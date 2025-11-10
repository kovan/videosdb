from basilisp.main import bootstrap


def invoke_cli():
     bootstrap("videosdb.run:entrypoint")

if __name__ == "__main__":
    invoke_cli()