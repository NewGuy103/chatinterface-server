from setuptools import setup, find_packages

with open("README.md", 'r') as f:
    readme_text: str = f.read()

setup(
    name="newguy103-chatinterface-server",
    version='0.1.0',
    description="A simple centralized, self-hosted server for chatting.",
    long_description=readme_text,
    long_description_content_type="text/markdown",
    author="NewGuy103",
    author_email="userchouenthusiast@gmail.com",
    install_requires=[
        "mariadb",
        "fastapi[standard]",
        "argon2-cffi",
        "sqlmodel",
        "uvicorn[standard]",
        "pydantic-settings"
    ],
    license="MPL 2.0",
    packages=find_packages()
)
