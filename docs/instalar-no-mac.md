# Instalar o Sextou no Mac

Este guia vale para a release `v0.2.0-rc.2` em **Mac com chip Apple**.

```text
① conferir o Mac  →  ② baixar e validar  →  ③ ver a prévia  →  ④ aplicar
```

## Instalação nova

### 1. Confira os três requisitos

- ✅ Mac com chip Apple, usando o Terminal em modo nativo
- ✅ Node `v24.21.0`
- ✅ GitHub CLI já autenticado e com acesso de leitura ao SextouCore

O bootstrap apenas confere. Ele não instala programas, não abre login, não
compra nada e não troca para outro repositório ou provedor sozinho.

### 2. Rode a prévia

Escolha uma rota do contrato: `claude`, `codex`, `gemini`, `opencode`, `local`
ou `codex-local`.

> 🚫 **NÃO PUBLICAR AINDA:** o valor abaixo é um marcador. Depois do commit A
> do script, o commit B precisa trocar `BOOTSTRAP_SOURCE_SHA` pelo SHA completo
> e imutável daquele commit, mudar `source_sha_status` para `verified_commit_a`
> e `publishable` para `true` em `release.json`. O gate só aceita a publicação
> se o commit existir, for ancestral do commit B e contiver exatamente os mesmos
> bytes do `install.sh` atual.

```bash
BOOTSTRAP_SOURCE_SHA="NAO_PUBLICAR_ATE_COMMIT_A"
/bin/bash -c "$(curl -fsSL "https://raw.githubusercontent.com/kewinho-prog/sextou-install/$BOOTSTRAP_SOURCE_SHA/install.sh")" -- --provedor codex
```

O nome aceito pelo bootstrap é só a sua escolha. A prévia do Core confirma se
essa release realmente tem um lançador para a rota. Se não tiver, ela para com
um código estável e não salva configuração.

Durante a prévia, o bootstrap:

- baixa apenas a tag `v0.2.0-rc.2` para uma área temporária;
- compara a tag com o SHA fixado;
- busca `origin/main` e prova que o SHA faz parte desse histórico;
- executa o Core sem `--aplicar`;
- só cria `~/.sextou/core` depois que a prévia termina com sucesso.

### 3. Aplique

No final da prévia aparece um comando já pronto. Confira o que foi mostrado e
rode esse comando. No destino padrão, ele se parece com isto:

```bash
bash "$HOME/.sextou/core/instalador/instalar.sh" --adaptativo --aplicar --provedor codex
```

Troque `codex` somente se essa foi a rota usada na prévia.

### 4. Abra a primeira conversa

Use o comando indicado pelo Core depois da aplicação. A primeira resposta da
IA precisa ser exatamente:

> Como você quer me chamar?

Responda com o nome desejado. Se aparecer outra frase, pare e guarde a saída do
Terminal: a identidade ainda não foi confirmada.

## Atualização de quem já instalou

Não rode o bootstrap novamente. Ele vai parar com
`BOOTSTRAP_ALREADY_INSTALLED` para proteger o checkout existente.

Use o atualizador do próprio Core:

```bash
bash "$HOME/.sextou/core/instalador/atualizar.sh"
```

Isso inclui instalações antigas que ainda dependem de Node 20. O bootstrap de
instalação nova recusa Node 20; a transição pertence ao atualizador.

Se a instalação ainda estiver no caminho antigo `~/.prima/core`, use o
atualizador de lá. Ele é o ponto de entrada responsável por tratar essa
instalação; não mova o checkout manualmente:

```bash
bash "$HOME/.prima/core/instalador/atualizar.sh"
```

## Recuperação sem apagar nada

| Mensagem | O que fazer |
|---|---|
| `GITHUB_LOGIN_REQUIRED` | Rode `gh auth login` separadamente e depois repita a instalação. |
| `CORE_RELEASE_NOT_FOUND` | Confirme que a tag foi publicada e que sua conta tem acesso. Não use `main` como atalho. |
| `CORE_RELEASE_MISMATCH` | Pare. A tag e o SHA não combinam; peça uma release corrigida. |
| `CORE_RELEASE_OUTSIDE_MAIN` | Pare. O SHA ainda não pertence ao histórico de `origin/main`. |
| `CORE_PREVIEW_FAILED` | Leia o código exibido pelo Core e escolha uma rota que tenha lançador nessa release. |
| `PARENT_IDENTITY_CHANGED` | Preserve o staging indicado. A pasta-pai mudou durante a prévia e nenhum caminho substituto foi usado. |
| `BOOTSTRAP_ALREADY_INSTALLED` | Use `instalador/atualizar.sh`; não reinstale por cima. |
| `LEGACY_PRIMA_INSTALLATION` | Use o atualizador dentro de `~/.prima/core`. |

Se uma execução antiga deixou uma pasta incompleta que não é reconhecida como
checkout, preserve-a com outro nome antes de tentar de novo:

```bash
mv "$HOME/.sextou/core" "$HOME/.sextou/core-incompleto-$(date +%Y%m%d-%H%M%S)"
```

Esse comando move o conteúdo; não apaga. Se o Core mostrar um caminho de
recuperação ou journal, preserve esse caminho até a instalação ser verificada.
