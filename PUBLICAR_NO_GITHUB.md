# Publicação no GitHub

Repositório proposto: `angelohafner/three-phase-scr-rectifier-visualizer`.

O arquivo `publicar_no_github.bat` automatiza a publicação no Windows, **após a autenticação na sua conta GitHub**.

## Pré-requisitos

- Python 3.10 ou superior, para executar o programa (não é necessário para publicar).
- Git instalado (https://git-scm.com/downloads/win).
- GitHub CLI instalado (https://cli.github.com/), por exemplo `winget install --id GitHub.cli -e`.

## Publicação automática no Windows

1. Extraia o ZIP e entre na pasta `three-phase-scr-rectifier-visualizer`.
2. Execute `publicar_no_github.bat`.
3. Caso seja necessário, faça login no navegador com o GitHub CLI. Verifique se a conta autenticada é `angelohafner`.
4. O script inicializa o Git, faz o commit inicial e cria o repositório **privado**, enviando os arquivos.

Se o Git solicitar uma identidade para o commit, configure seu nome e e-mail na máquina:

```bash
git config --global user.name "Seu Nome"
git config --global user.email "email-da-sua-conta@example.com"
```

Execute novamente `publicar_no_github.bat`.

## Alternativa: publicação manual pelo GitHub CLI

Na pasta do projeto, execute:

```bash
gh auth login
git init -b main
git add .
git commit -m "Initial release: twelve-state SCR rectifier visualization"
gh repo create angelohafner/three-phase-scr-rectifier-visualizer --private --source=. --remote=origin --push
```

O comando oficial `gh repo create --source=. --push` cria o repositório remoto a partir dos arquivos locais e envia o commit. A escolha inicial por **privado** evita publicar o conteúdo sem revisão prévia. Para torná-lo público depois, use as configurações de visibilidade do repositório no GitHub.

## Depois da publicação

Repositório: `https://github.com/angelohafner/three-phase-scr-rectifier-visualizer` (o endereço só passa a funcionar depois da criação).

O pacote inclui o programa Python, as configurações JSON, 15 testes, todos os 12 estados em SVG/PNG, o painel geral e manifestos de caminhos de condução.
