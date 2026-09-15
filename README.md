# Sextou — bootstrap público

Este repositório contém a porta de entrada pública para uma **instalação nova**
do SextouCore privado. O bootstrap não instala dependências, não faz login, não
compra serviços e não usa fallback remoto.

## Instalar

Matriz homologada desta release:

- macOS em Apple Silicon (`arm64`);
- Node `v24.21.0`;
- Git e GitHub CLI já autenticado;
- acesso de leitura a `kewinho-prog/SextouCore`.

> 🚫 **NÃO PUBLICAR AINDA:** `BOOTSTRAP_SOURCE_SHA` será preenchido com o
> commit A que contém o script. O marcador abaixo precisa ser trocado no commit
> B antes de divulgar a instalação. Nesse commit B, o manifesto também muda
> para `source_sha_status: verified_commit_a` e `publishable: true`; o gate
> confere existência, ancestralidade e igualdade byte a byte do script.

```bash
BOOTSTRAP_SOURCE_SHA="NAO_PUBLICAR_ATE_COMMIT_A"
/bin/bash -c "$(curl -fsSL "https://raw.githubusercontent.com/kewinho-prog/sextou-install/$BOOTSTRAP_SOURCE_SHA/install.sh")" -- --provedor codex
```

O contrato aceita `claude`, `codex`, `gemini`, `opencode`, `local` e
`codex-local`. Isso valida apenas o nome pedido. A prévia do SextouCore é quem
confirma se a release fixada possui um lançador para a rota; o bootstrap nunca
declara autenticação, funcionamento ou custo como comprovados.

O processo usa dois estágios:

1. o bootstrap clona uma tag numa pasta temporária, confere tag + SHA, busca
   `origin/main` e prova que o SHA pertence ao histórico publicado antes de
   executar somente a prévia do Core;
2. depois de uma prévia bem-sucedida, ele cria `~/.sextou/core` e mostra o
   comando exato com `--aplicar` para a pessoa executar.

Release fixada:

| Campo | Valor |
|---|---|
| Tag | `v0.2.0-rc.2` |
| SHA fixado | [`release.json`](release.json) |

Se a tag não existir, apontar para outro SHA ou estiver fora do histórico de
`origin/main`, nada do Core é executado. `main` serve apenas como prova de
proveniência; nunca vira versão alternativa.

Node 20, 23 e 25 são recusados. Versões 24 diferentes de `24.21.0` também
ficam fora desta matriz até serem homologadas. A transição de instalações
antigas em Node 20 pertence ao atualizador, não ao bootstrap de instalação nova.

## Atualizar

O bootstrap recusa qualquer checkout já existente e aponta para o atualizador:

```bash
bash "$HOME/.sextou/core/instalador/atualizar.sh"
```

Uma instalação antiga em `~/.prima/core` também bloqueia uma instalação nova;
use o atualizador que já existe nesse caminho. Não há migração ou sobrescrita
automática no bootstrap.

O passo a passo visual, a aplicação e a recuperação sem apagar arquivos estão
em [docs/instalar-no-mac.md](docs/instalar-no-mac.md).

Depois da aplicação, a primeira conversa precisa começar com a resposta exata:

> Como você quer me chamar?

## Verificar localmente

Os testes criam um repositório Git sintético local. Não acessam o SextouCore,
GitHub, contas ou dados pessoais.

```bash
bash -n install.sh
python3 -m unittest discover -s tests -v
git diff --check
```

O CI executa as mesmas verificações. `release.json` e o bloco de pin em
`install.sh` são comparados por teste para que a troca do SHA seja pequena e
revisável.
