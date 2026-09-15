#!/usr/bin/env bash
# install.sh — bootstrap público e fixado do SextouCore privado.
#
# Uso local durante a preparação da release:
#   bash install.sh --provedor codex
#
# O bootstrap faz uma instalação NOVA. Ele baixa uma release fixada, confere
# tag + SHA, executa somente a prévia do instalador do Core e então mostra o
# comando de aplicação. Instalações existentes seguem pelo atualizador.
set -uo pipefail

# Atualização de release: altere somente este bloco e release.json no mesmo PR.
CORE_REPOSITORY="kewinho-prog/SextouCore"
CORE_RELEASE_TAG="v0.2.0-rc.2"
CORE_RELEASE_SHA="9c9598795ddb8276c1667e825b3934e2b67ce802"
NODE_HOMOLOGATED="24.21.0"
BOOTSTRAP_MARKER_REL=".git/sextou-bootstrap-complete"
BOOTSTRAP_MARKER_EXPECTED="$(printf 'schema=1\nrepository=%s' "$CORE_REPOSITORY")"
CORE_LEGACY_REQUIRED_FILES=(
  package.json
  instalador/atualizar.sh
  instalador/instalar.sh
  instalador/mensagens.sh
  instalador/verificar-configuracao.sh
  lib/lock-legado.sh
  lib/estado.sh
  lib/identidade.sh
)

DESTINO="${SEXTOU_CORE:-${HOME:-}/.sextou/core}"
TEST_MODE="${SEXTOU_BOOTSTRAP_TEST_MODE:-0}"

if [[ -t 1 ]]; then
  V=$'\033[32m'; A=$'\033[33m'; E=$'\033[31m'; D=$'\033[2m'; F=$'\033[0m'
else
  V=''; A=''; E=''; D=''; F=''
fi
ok()    { printf '  %s✓%s %s\n' "$V" "$F" "$1"; }
aviso() { printf '  %s!%s %s\n' "$A" "$F" "$1"; }
falha() {
  printf '\n  %s✗ %s%s\n    %spor quê:%s %s\n    %so que fazer:%s %s\n' \
    "$E" "$1" "$F" "$D" "$F" "$2" "$D" "$F" "$3" >&2
}

# ── Contrato de argumentos ──────────────────────────────────────────────────
# O allowlist aceita todas as rotas do contrato. Aceitar o nome NÃO afirma que
# a rota funciona: o Core fixado precisa possuir e validar o lançador.
PROVEDOR=""
VIU_PROVEDOR=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --provedor)
      if (( VIU_PROVEDOR == 1 )); then
        falha "ARGUMENTO_INVALIDO" "--provedor foi repetido" "informe a opção uma vez"
        exit 2
      fi
      if [[ $# -lt 2 || -z "${2//[[:space:]]/}" || "$2" == --* ]]; then
        falha "ARGUMENTO_INVALIDO" "faltou o valor de --provedor" \
          "escolha claude, codex, gemini, opencode, local ou codex-local"
        exit 2
      fi
      case "$2" in
        claude|codex|gemini|opencode|local|codex-local) PROVEDOR="$2" ;;
        *)
          falha "ARGUMENTO_INVALIDO" "provedor fora do contrato" \
            "escolha claude, codex, gemini, opencode, local ou codex-local"
          exit 2 ;;
      esac
      VIU_PROVEDOR=1
      shift 2
      ;;
    *)
      falha "ARGUMENTO_INVALIDO" "opção não reconhecida: $1" \
        "use somente --provedor; este bootstrap instala apenas a matriz nova homologada"
      exit 2
      ;;
  esac
done

if [[ -n "${PRIMA_CORE:-}" && -z "${SEXTOU_CORE:-}" ]]; then
  falha "LEGACY_DESTINATION_VARIABLE" "PRIMA_CORE pertence ao instalador antigo" \
    "preserve a instalação existente e use o atualizador dela; para uma instalação nova, use SEXTOU_CORE"
  exit 1
fi

if [[ -z "${HOME:-}" || "$HOME" != /* ]]; then
  falha "HOME_INVALIDO" "não há uma pasta pessoal absoluta disponível" \
    "abra um Terminal normal do macOS e rode novamente"
  exit 1
fi
case "$DESTINO" in
  ""|/|"$HOME"|*'/../'*|*/..|*'/./'*|*/.|*'//'*)
    falha "DESTINO_INVALIDO" "o destino não é específico e seguro" \
      "use o padrão ~/.sextou/core ou um caminho absoluto em SEXTOU_CORE"
    exit 1 ;;
esac
if [[ "$DESTINO" != /* || "$DESTINO" == *$'\n'* || "$DESTINO" == *$'\r'* ]]; then
  falha "DESTINO_INVALIDO" "o destino precisa ser um caminho absoluto em uma linha" \
    "use o padrão ~/.sextou/core ou um caminho absoluto em SEXTOU_CORE"
  exit 1
fi

# Há um único desvio interno para os testes offline. Ele exige três valores
# explícitos, aceita somente repositório local absoluto e nunca é documentado
# como rota de instalação.
CORE_CLONE_URL="https://github.com/$CORE_REPOSITORY.git"
if [[ "$TEST_MODE" == "1" ]]; then
  CORE_CLONE_URL="${SEXTOU_BOOTSTRAP_TEST_REPO:-}"
  CORE_RELEASE_TAG="${SEXTOU_BOOTSTRAP_TEST_TAG:-}"
  CORE_RELEASE_SHA="${SEXTOU_BOOTSTRAP_TEST_SHA:-}"
  if [[ "$CORE_CLONE_URL" != /* || ! -d "$CORE_CLONE_URL" || -z "$CORE_RELEASE_TAG" || \
        ! "$CORE_RELEASE_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    falha "TEST_CONFIG_INVALID" "a configuração do teste offline está incompleta" \
      "informe repositório local absoluto, tag e SHA de 40 caracteres"
    exit 2
  fi
elif [[ "$TEST_MODE" != "0" ]]; then
  falha "TEST_CONFIG_INVALID" "o modo interno de teste só aceita 0 ou 1" "remova SEXTOU_BOOTSTRAP_TEST_MODE"
  exit 2
fi

verificar_ancestrais_sem_symlink() {
  local atual="$1" pai
  while [[ "$atual" != "/" && "$atual" != "." && -n "$atual" ]]; do
    [[ -L "$atual" ]] && return 1
    pai="$(dirname "$atual")"
    [[ "$pai" == "$atual" ]] && break
    atual="$pai"
  done
  return 0
}

marcador_bootstrap_valido() {
  local alvo="$1" marcador="$1/$BOOTSTRAP_MARKER_REL" conteudo
  [[ -f "$marcador" && ! -L "$marcador" ]] || return 1
  conteudo="$(command cat "$marcador" 2>/dev/null || true)"
  [[ "$conteudo" == "$BOOTSTRAP_MARKER_EXPECTED" ]]
}

checkout_core_validado() {
  local alvo="$1" remoto estado relativo arquivo
  command -v git >/dev/null 2>&1 || return 1
  [[ -d "$alvo" && ( -d "$alvo/.git" || -f "$alvo/.git" ) ]] || return 1
  [[ "$(git -C "$alvo" rev-parse --is-inside-work-tree 2>/dev/null || true)" == true ]] || return 1
  git -C "$alvo" rev-parse --verify 'HEAD^{commit}' >/dev/null 2>&1 || return 1
  remoto="$(git -C "$alvo" remote get-url origin 2>/dev/null || true)"
  case "$remoto" in
    "https://github.com/$CORE_REPOSITORY.git"|"https://github.com/$CORE_REPOSITORY"|\
    "git@github.com:$CORE_REPOSITORY.git"|"ssh://git@github.com/$CORE_REPOSITORY.git") ;;
    *) return 1 ;;
  esac
  for relativo in "${CORE_LEGACY_REQUIRED_FILES[@]}"; do
    arquivo="$alvo/$relativo"
    [[ -f "$arquivo" && ! -L "$arquivo" ]] || return 1
  done
  git -C "$alvo" ls-files --error-unmatch \
    "${CORE_LEGACY_REQUIRED_FILES[@]}" >/dev/null 2>&1 || return 1
  estado="$(git -C "$alvo" status --porcelain 2>/dev/null)" || return 1
  [[ -z "$estado" ]] || return 1
  grep -Eq '"name"[[:space:]]*:[[:space:]]*"sextou-core"' "$alvo/package.json" || return 1
  grep -Eq '"version"[[:space:]]*:[[:space:]]*"[0-9]+\.[0-9]+\.[0-9]+([.-][^"]+)?"' \
    "$alvo/package.json" || return 1
  for relativo in instalador/atualizar.sh instalador/instalar.sh \
    instalador/mensagens.sh instalador/verificar-configuracao.sh \
    lib/lock-legado.sh lib/estado.sh lib/identidade.sh; do
    bash -n "$alvo/$relativo" >/dev/null 2>&1 || return 1
  done
  return 0
}

identidade_fisica_diretorio() {
  local alvo="$1" identidade
  identidade="$(stat -L -f '%d:%i' "$alvo" 2>/dev/null || true)"
  if [[ "$identidade" =~ ^[0-9]+:[0-9]+$ ]]; then
    printf '%s\n' "$identidade"
    return 0
  fi
  identidade="$(stat -L -c '%d:%i' "$alvo" 2>/dev/null || true)"
  [[ "$identidade" =~ ^[0-9]+:[0-9]+$ ]] || return 1
  printf '%s\n' "$identidade"
}

if ! verificar_ancestrais_sem_symlink "$DESTINO"; then
  falha "DESTINATION_SYMLINK" "o destino passa por um link simbólico" \
    "use um caminho real, sem atalhos no meio"
  exit 1
fi

# Bootstrap é somente para instalação nova. Esta recusa acontece antes de
# login, acesso remoto, criação de pasta ou execução do Core.
if [[ -e "$DESTINO" || -L "$DESTINO" ]]; then
  if marcador_bootstrap_valido "$DESTINO" || checkout_core_validado "$DESTINO"; then
    falha "BOOTSTRAP_ALREADY_INSTALLED" "já existe um checkout em $DESTINO" \
      "não rode o bootstrap de novo; atualize com: bash \"$DESTINO/instalador/atualizar.sh\""
  else
    falha "DESTINATION_OCCUPIED" "já existe conteúdo parcial ou não reconhecido em $DESTINO" \
      "preserve esse conteúdo, mova-o para outro nome e só então tente uma instalação nova"
  fi
  exit 1
fi

PRIMA_ANTIGO="$HOME/.prima/core"
if [[ -e "$PRIMA_ANTIGO" || -L "$PRIMA_ANTIGO" ]]; then
  falha "LEGACY_PRIMA_INSTALLATION" "foi encontrada uma instalação antiga em $PRIMA_ANTIGO" \
    "não crie uma segunda instalação; atualize com: bash \"$PRIMA_ANTIGO/instalador/atualizar.sh\""
  exit 1
fi

cat <<ABERTURA

  Sextou — instalação nova

  Release fixada: $CORE_RELEASE_TAG
  Esta etapa confere o Mac, baixa o Core privado, valida tag + SHA e
  mostra uma prévia. Nenhuma configuração é aplicada automaticamente.

ABERTURA

# ── Plataforma homologada ────────────────────────────────────────────────────
SO="$(uname -s 2>/dev/null || true)"
ARQUITETURA="$(uname -m 2>/dev/null || true)"
if [[ "$SO" != "Darwin" || "$ARQUITETURA" != "arm64" ]]; then
  falha "PLATFORM_UNSUPPORTED" "esta release foi homologada somente em macOS Apple Silicon (arm64)" \
    "use um Mac Apple Silicon em Terminal nativo; outros sistemas precisam de uma release homologada"
  exit 1
fi
ok "macOS Apple Silicon"

# ── Pré-requisitos: conferir, nunca instalar ─────────────────────────────────
if ! command -v git >/dev/null 2>&1; then
  falha "GIT_REQUIRED" "git não está disponível" "instale as ferramentas da Apple com: xcode-select --install"
  exit 1
fi
ok "git"

if ! command -v node >/dev/null 2>&1; then
  falha "NODE_REQUIRED" "Node não está disponível" \
    "instale Node $NODE_HOMOLOGATED pela fonte oficial e rode novamente"
  exit 1
fi
NODE_VERSION_RAW="$(node -v 2>/dev/null)"
NODE_STATUS=$?
if (( NODE_STATUS != 0 )) || [[ ! "$NODE_VERSION_RAW" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
  falha "NODE_VERSION_UNSUPPORTED" "não foi possível reconhecer a versão do Node" \
    "use Node v$NODE_HOMOLOGATED"
  exit 1
fi
NODE_VERSION="${NODE_VERSION_RAW#v}"
if [[ "$NODE_VERSION" == "$NODE_HOMOLOGATED" ]]; then
  ok "Node v$NODE_VERSION homologado"
else
  falha "NODE_VERSION_UNSUPPORTED" "Node v$NODE_VERSION não pertence à matriz desta release" \
    "use Node v$NODE_HOMOLOGATED; instalações antigas em Node 20 devem seguir pelo atualizador"
  exit 1
fi

if [[ "$TEST_MODE" == "0" ]]; then
  if ! command -v gh >/dev/null 2>&1; then
    falha "GITHUB_CLI_REQUIRED" "o cliente gh não está disponível" \
      "instale o GitHub CLI e autentique fora deste bootstrap"
    exit 1
  fi
  if ! gh auth status >/dev/null 2>&1; then
    falha "GITHUB_LOGIN_REQUIRED" "não há uma sessão válida no GitHub CLI" \
      "faça o login separadamente com: gh auth login; depois rode este bootstrap de novo"
    exit 1
  fi
  ok "sessão do GitHub já existente"

  if ! gh repo view "$CORE_REPOSITORY" --json nameWithOwner >/dev/null 2>&1; then
    falha "CORE_ACCESS_DENIED" "a conta atual não consegue ler $CORE_REPOSITORY" \
      "peça acesso de leitura a quem forneceu o Sextou; não há repositório alternativo"
    exit 1
  fi
  ok "acesso ao Core privado"
else
  ok "fonte Git local do teste offline"
fi

# ── Clone temporário e pin verificável ───────────────────────────────────────
DESTINO_PAI="$(dirname "$DESTINO")"
if ! mkdir -p "$DESTINO_PAI"; then
  falha "DESTINATION_CREATE_FAILED" "não foi possível preparar a pasta de destino" \
    "confira as permissões de $DESTINO_PAI"
  exit 1
fi
if ! verificar_ancestrais_sem_symlink "$DESTINO"; then
  falha "DESTINATION_SYMLINK" "o destino mudou para um link simbólico durante a preparação" \
    "preserve o que existe e escolha outro caminho real"
  exit 1
fi
PARENT_ID_BEFORE_CD="$(identidade_fisica_diretorio "$DESTINO_PAI" 2>/dev/null || true)"
if [[ -z "$PARENT_ID_BEFORE_CD" ]]; then
  falha "PARENT_IDENTITY_CHANGED" "não foi possível identificar a pasta-pai preparada" \
    "nenhum checkout foi criado; preserve os caminhos envolvidos e tente outro destino"
  exit 1
fi

# O cwd é o descritor implícito da pasta física original. Daqui em diante,
# staging, cleanup, claim, cópia e verificação usam caminhos relativos a ele;
# trocar o nome lexical por um symlink não redireciona nenhuma mutação.
if ! cd -P "$DESTINO_PAI"; then
  falha "DESTINATION_CREATE_FAILED" "não foi possível ancorar a pasta física de destino" \
    "confira as permissões de $DESTINO_PAI"
  exit 1
fi
PARENT_ID_ORIGINAL="$(identidade_fisica_diretorio . 2>/dev/null || true)"
if [[ -z "$PARENT_ID_ORIGINAL" || "$PARENT_ID_ORIGINAL" != "$PARENT_ID_BEFORE_CD" || \
      "$(identidade_fisica_diretorio "$DESTINO_PAI" 2>/dev/null || true)" != "$PARENT_ID_ORIGINAL" ]]; then
  falha "PARENT_IDENTITY_CHANGED" "a pasta-pai mudou durante a ancoragem" \
    "nenhum checkout foi criado; preserve os caminhos envolvidos e tente outro destino"
  exit 1
fi
DESTINO_NOME="$(basename "$DESTINO")"

STAGING_ROOT="$(mktemp -d '.sextou-bootstrap.XXXXXX' 2>/dev/null || true)"
if [[ -z "$STAGING_ROOT" || ! -d "$STAGING_ROOT" ]]; then
  falha "STAGING_CREATE_FAILED" "não foi possível criar a área temporária" \
    "confira espaço e permissões em $DESTINO_PAI"
  exit 1
fi
CHECKOUT_TEMP="$STAGING_ROOT/core"
PRESERVAR_STAGING=0
RECUPERACAO_REPORTADA=0

parent_lexical_ainda_original() {
  local atual
  atual="$(identidade_fisica_diretorio "$DESTINO_PAI" 2>/dev/null || true)"
  [[ -n "$atual" && "$atual" == "$PARENT_ID_ORIGINAL" ]]
}

reportar_parent_trocado() {
  local parent_recuperacao staging_recuperacao
  PRESERVAR_STAGING=1
  RECUPERACAO_REPORTADA=1
  parent_recuperacao="$(pwd -P 2>/dev/null || true)"
  if [[ -n "$parent_recuperacao" ]]; then
    staging_recuperacao="$parent_recuperacao/${STAGING_ROOT#./}"
  else
    staging_recuperacao="staging ${STAGING_ROOT#./} no diretório físico $PARENT_ID_ORIGINAL"
  fi
  falha "PARENT_IDENTITY_CHANGED" "a pasta-pai original foi movida ou substituída durante a prévia" \
    "nenhum caminho substituto foi tocado; o staging foi preservado em: $staging_recuperacao"
}

limpar_temporario() {
  if (( PRESERVAR_STAGING == 1 )) || ! parent_lexical_ainda_original; then
    if (( RECUPERACAO_REPORTADA == 0 )); then
      reportar_parent_trocado
    fi
    return
  fi
  if [[ -n "${STAGING_ROOT:-}" && -d "$STAGING_ROOT" ]]; then
    case "$STAGING_ROOT" in
      .sextou-bootstrap.*) rm -rf -- "$STAGING_ROOT" ;;
    esac
  fi
}
trap limpar_temporario EXIT
trap 'exit 130' HUP INT TERM

echo "  Baixando somente $CORE_RELEASE_TAG..."
if [[ "$TEST_MODE" == "1" ]]; then
  git clone --quiet --no-checkout --single-branch --branch "$CORE_RELEASE_TAG" \
    "$CORE_CLONE_URL" "$CHECKOUT_TEMP" 2>"$STAGING_ROOT/git-clone.err"
  CLONE_STATUS=$?
else
  git -c credential.helper= -c 'credential.helper=!gh auth git-credential' \
    clone --quiet --no-checkout --single-branch --branch "$CORE_RELEASE_TAG" \
    "$CORE_CLONE_URL" "$CHECKOUT_TEMP" 2>"$STAGING_ROOT/git-clone.err"
  CLONE_STATUS=$?
fi
if (( CLONE_STATUS != 0 )); then
  falha "CORE_RELEASE_NOT_FOUND" "não foi possível obter a tag fixada $CORE_RELEASE_TAG" \
    "confirme acesso e publicação da release; main não será usado como versão alternativa"
  exit 1
fi

TAG_SHA="$(git -C "$CHECKOUT_TEMP" rev-parse --verify "refs/tags/$CORE_RELEASE_TAG^{commit}" 2>/dev/null || true)"
if [[ "$TAG_SHA" != "$CORE_RELEASE_SHA" ]]; then
  falha "CORE_RELEASE_MISMATCH" "a tag $CORE_RELEASE_TAG aponta para um commit diferente do pin esperado" \
    "interrompa e peça uma release cujo tag e SHA coincidam; nenhum código foi executado"
  exit 1
fi
MAIN_REFSPEC='+refs/heads/main:refs/remotes/origin/main'
if ! git -C "$CHECKOUT_TEMP" config --replace-all remote.origin.fetch "$MAIN_REFSPEC"; then
  falha "CORE_MAIN_NOT_FOUND" "não foi possível preparar a prova contra origin/main" \
    "interrompa e peça uma release corrigida"
  exit 1
fi
if [[ "$TEST_MODE" == "1" ]]; then
  git -C "$CHECKOUT_TEMP" fetch --quiet --no-tags origin "$MAIN_REFSPEC" \
    2>"$STAGING_ROOT/git-main.err"
  MAIN_FETCH_STATUS=$?
else
  git -C "$CHECKOUT_TEMP" -c credential.helper= \
    -c 'credential.helper=!gh auth git-credential' \
    fetch --quiet --no-tags origin "$MAIN_REFSPEC" 2>"$STAGING_ROOT/git-main.err"
  MAIN_FETCH_STATUS=$?
fi
if (( MAIN_FETCH_STATUS != 0 )) || \
   ! git -C "$CHECKOUT_TEMP" rev-parse --verify "refs/remotes/origin/main^{commit}" >/dev/null 2>&1; then
  falha "CORE_MAIN_NOT_FOUND" "origin/main não pôde ser obtida para validar a proveniência da release" \
    "confirme acesso e publicação de main; nenhum código do Core foi executado"
  exit 1
fi
if ! git -C "$CHECKOUT_TEMP" merge-base --is-ancestor \
     "$CORE_RELEASE_SHA" refs/remotes/origin/main; then
  falha "CORE_RELEASE_OUTSIDE_MAIN" "o SHA fixado não pertence ao histórico publicado de origin/main" \
    "não execute esta release; integre o commit em main e publique um novo pin"
  exit 1
fi
ok "SHA pertence ao histórico de origin/main"

if ! git -C "$CHECKOUT_TEMP" checkout --quiet -B main "$CORE_RELEASE_SHA"; then
  falha "CORE_CHECKOUT_FAILED" "o commit conferido não pôde ser preparado" \
    "preserve a mensagem e peça uma nova release"
  exit 1
fi
HEAD_SHA="$(git -C "$CHECKOUT_TEMP" rev-parse --verify HEAD 2>/dev/null || true)"
BRANCH_ATUAL="$(git -C "$CHECKOUT_TEMP" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
REFSPEC_ATUAL="$(git -C "$CHECKOUT_TEMP" config --get-all remote.origin.fetch 2>/dev/null || true)"
if [[ "$HEAD_SHA" != "$CORE_RELEASE_SHA" || "$BRANCH_ATUAL" != "main" || \
      "$REFSPEC_ATUAL" != "$MAIN_REFSPEC" || \
      -n "$(git -C "$CHECKOUT_TEMP" status --porcelain 2>/dev/null)" ]]; then
  falha "CORE_CHECKOUT_FAILED" "o checkout final não reproduz exatamente o pin esperado" \
    "interrompa e peça uma nova release"
  exit 1
fi
ok "tag e SHA conferidos: $CORE_RELEASE_TAG · $CORE_RELEASE_SHA"

# ── Prévia do Core: jamais aplicar, jamais prometer uma rota ─────────────────
ADAPTATIVO="$CHECKOUT_TEMP/instalador/instalar.sh"
MODULO_ADAPTATIVO="$CHECKOUT_TEMP/instalador/instalar-adaptativo.mjs"
ATUALIZADOR="$CHECKOUT_TEMP/instalador/atualizar.sh"
if [[ ! -f "$ADAPTATIVO" || -L "$ADAPTATIVO" || ! -f "$MODULO_ADAPTATIVO" || \
      -L "$MODULO_ADAPTATIVO" || ! -f "$ATUALIZADOR" || -L "$ATUALIZADOR" ]] || \
   ! git -C "$CHECKOUT_TEMP" ls-files --error-unmatch instalador/instalar.sh \
      instalador/instalar-adaptativo.mjs instalador/atualizar.sh >/dev/null 2>&1 || \
   ! bash -n "$ADAPTATIVO"; then
  falha "ADAPTIVE_INSTALLER_UNAVAILABLE" "a release fixada não contém um lançador adaptativo íntegro" \
    "não use um instalador antigo; peça uma release corrigida"
  exit 1
fi

ARGS_PREVIA=(--adaptativo)
[[ -n "$PROVEDOR" ]] && ARGS_PREVIA+=(--provedor "$PROVEDOR")

echo ""
if [[ -n "$PROVEDOR" ]]; then
  aviso "rota solicitada: $PROVEDOR; somente o Core pode confirmar se há lançador nesta release"
else
  aviso "nenhuma rota foi presumida; o Core pedirá uma escolha se o terminal permitir"
fi
echo "  Abrindo a prévia do Core. Nenhuma opção de aplicação será enviada."
echo ""

bash "$ADAPTATIVO" "${ARGS_PREVIA[@]}"
PREVIEW_STATUS=$?
if (( PREVIEW_STATUS != 0 )); then
  if (( PREVIEW_STATUS == 130 )); then
    falha "PREVIEW_CANCELLED" "a prévia foi cancelada" "rode novamente quando quiser; nada foi instalado"
    exit 130
  fi
  falha "CORE_PREVIEW_FAILED" "o Core recusou ou não conseguiu validar a rota (código $PREVIEW_STATUS)" \
    "use o código estável exibido pelo Core; nenhuma configuração foi aplicada e o destino continua livre"
  exit "$PREVIEW_STATUS"
fi

# O destino definitivo só nasce depois do pin e da prévia. mkdir reivindica o
# caminho de forma atômica: se outro processo chegou primeiro, falha em vez de
# permitir que mv aninhe o checkout dentro do diretório concorrente.
if ! parent_lexical_ainda_original; then
  reportar_parent_trocado
  exit 1
fi
if [[ -e "$DESTINO_NOME" || -L "$DESTINO_NOME" ]]; then
  falha "DESTINATION_RACE" "o destino passou a existir durante a prévia" \
    "preserve o conteúdo novo e rode novamente com outro destino"
  exit 1
fi
if ! mkdir "$DESTINO_NOME" 2>/dev/null; then
  falha "DESTINATION_RACE" "não foi possível reivindicar o destino; ele pode ter sido criado por outro processo" \
    "preserve o que existe em $DESTINO e rode novamente com outro destino"
  exit 1
fi
if ! parent_lexical_ainda_original; then
  rmdir "$DESTINO_NOME" 2>/dev/null || true
  reportar_parent_trocado
  exit 1
fi
if ! cp -pR "$CHECKOUT_TEMP/." "$DESTINO_NOME/"; then
  falha "INSTALLATION_FINALIZE_FAILED" "a cópia para o destino reivindicado não foi concluída" \
    "preserve $DESTINO como recuperação parcial, mova-o para outro nome e tente novamente"
  exit 1
fi
if ! parent_lexical_ainda_original; then
  reportar_parent_trocado
  exit 1
fi
FINAL_HEAD="$(git -C "$DESTINO_NOME" rev-parse --verify HEAD 2>/dev/null || true)"
FINAL_BRANCH="$(git -C "$DESTINO_NOME" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
FINAL_REFSPEC="$(git -C "$DESTINO_NOME" config --get-all remote.origin.fetch 2>/dev/null || true)"
if [[ "$FINAL_HEAD" != "$CORE_RELEASE_SHA" || "$FINAL_BRANCH" != "main" || \
      "$FINAL_REFSPEC" != "$MAIN_REFSPEC" || \
      -n "$(git -C "$DESTINO_NOME" status --porcelain 2>/dev/null)" ]]; then
  falha "INSTALLATION_FINALIZE_FAILED" "o destino copiado não preservou o checkout verificado" \
    "preserve $DESTINO como recuperação parcial, mova-o para outro nome e tente novamente"
  exit 1
fi
FINAL_UPDATER="$DESTINO_NOME/instalador/atualizar.sh"
if [[ ! -f "$FINAL_UPDATER" || -L "$FINAL_UPDATER" ]] || \
   ! git -C "$DESTINO_NOME" ls-files --error-unmatch instalador/atualizar.sh >/dev/null 2>&1; then
  falha "INSTALLATION_FINALIZE_FAILED" "o atualizador rastreado não chegou íntegro ao destino" \
    "preserve $DESTINO como recuperação parcial, mova-o para outro nome e tente novamente"
  exit 1
fi
if ! parent_lexical_ainda_original; then
  reportar_parent_trocado
  exit 1
fi
MARKER_TEMP="$DESTINO_NOME/.git/.sextou-bootstrap-complete.$$"
if ! printf '%s\n' "$BOOTSTRAP_MARKER_EXPECTED" > "$MARKER_TEMP" || \
   ! mv "$MARKER_TEMP" "$DESTINO_NOME/$BOOTSTRAP_MARKER_REL" || \
   ! marcador_bootstrap_valido "$DESTINO_NOME"; then
  falha "INSTALLATION_FINALIZE_FAILED" "o checkout foi copiado, mas não recebeu o marcador final" \
    "preserve $DESTINO como recuperação parcial e não rode o bootstrap por cima"
  exit 1
fi
if ! parent_lexical_ainda_original; then
  reportar_parent_trocado
  exit 1
fi
ok "Core preparado em $DESTINO"

ARGS_APLICAR=(--adaptativo --aplicar)
[[ -n "$PROVEDOR" ]] && ARGS_APLICAR+=(--provedor "$PROVEDOR")
CMD_APLICAR="bash $(printf '%q' "$DESTINO/instalador/instalar.sh")"
for argumento in "${ARGS_APLICAR[@]}"; do
  CMD_APLICAR+=" $(printf '%q' "$argumento")"
done

cat <<FINAL

  Prévia concluída. A configuração ainda não foi aplicada.

  Confira o resultado acima. Para aplicar exatamente esta escolha:

      $CMD_APLICAR

  Depois, abra a primeira conversa pelo comando indicado pelo Core.
  A primeira resposta precisa ser exatamente: Como você quer me chamar?

FINAL
