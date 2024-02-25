import github
import asyncio

ghtoken = github.Auth.Token("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")
xd = github.Github(auth=ghtoken)


def get_commits():
    
    return [commit for commit in xd.get_user().get_repo("discordmusicbot").get_commits()]

original_commits = get_commits()

async def Caca():
    global original_commits
    while True:
        await asyncio.sleep(1)
        new_commits = get_commits()
        if len(original_commits) < len(new_commits):
            print(f"Nueva actualización de código :nerd: :point_up:\n{new_commits[len(new_commits) -1].raw_data}\nBuggero: {new_commits[len(new_commits) - 1].author.login}")
            del new_commits
            original_commits = get_commits()

async def ejecutar():
    return await asyncio.wait_for(await Caca(), timeout=None)

for repo in xd.get_user().get_repos():
    print(f"""
Name: {repo.name}
author: {repo.owner.login}
""")

asyncio.run(ejecutar())


      

