# Sextou — bootstrap (instalador adaptativo, candidato)

> **Este caminho ainda é candidato, não publicado como padrão.** Ele existe
> para permitir começar com Codex (ou outro provedor suportado) sem
> precisar ter o Claude Code instalado antes. Não é prova de que o produto
> inteiro já foi instalado — só prepara o terreno e delega o diagnóstico e
> a prévia ao instalador adaptativo dentro do SextouCore.

## Comando

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/kewinho-prog/sextou-install/main/install.sh)" -- \
  --provedor codex
```

Ou, dentro deste repositório já baixado:

```bash
bash install.sh --provedor codex
```

Se o **SextouCore** já estiver baixado, execute dentro dele:

```bash
bash instalador/instalar.sh --adaptativo --provedor codex
```

As rotas do Core para novas instalações são `codex`, `opencode` e `local`
(OpenCode + Ollama). A rota exige seus executáveis disponíveis. O Core pode
planejar diretórios de configuração para Codex e OpenCode e criá-los somente
com `--aplicar`; isso não comprova login nem uma conversa real.

O bootstrap também reconhece `claude`, `gemini` e `codex-local`, mas o Core
recusa novas instalações dessas rotas sem lançador homologado. No modo
`--reaplicar-perfil` do **Core**, perfis legados coerentes são preservados sem
sondar provedores ou reescrever configuração, com estado `LEGACY_CONFIG_ONLY`.
`sextou conversar` recusa essas rotas com `ROTA_LEGADA_SEM_LANCADOR`, sem
fallback automático. Migração exige escolha explícita; `--reaplicar-perfil`
não é opção do bootstrap.

O que este script faz, em ordem:

1. **Confere** git, Node **24+** e o cliente `gh` — sem instalar nada sozinho; só sugere o comando oficial de cada dependência.
2. **Autentica** no repositório, só depois de você confirmar no terminal, e só se ainda não houver login. Sem terminal interativo e sem login, falha (não fica esperando).
3. **Confere o acesso** ao repositório separadamente do login: login válido não garante permissão de leitura.
4. **Reconhece** um checkout já existente sem mexer nele — sem fetch, sem merge, sem migração automática de `~/.prima`. Se o que existir não for um checkout do repositório esperado, for inesperado/não vazio, ou passar por um link simbólico, o script para e diz o que fazer.
5. **Baixa** por HTTPS quando ainda não existe checkout. Se falhar, nada é apagado à força e nenhuma mensagem de sucesso é exibida.
6. **Delega** ao instalador adaptativo do Core (`instalador/instalar.sh --adaptativo`), que faz o diagnóstico de verdade — provedor, credenciais, capacidades. Continua sendo prévia (config-preview): nada é aplicado. Se a prévia falhar, o código de saída é propagado e nenhuma instrução de aplicação é mostrada.
7. Mostra o comando exato para aplicar depois, com as mesmas opções escolhidas, mais `--aplicar` — `--aplicar` nunca é aceito nesta primeira invocação.

O instalador não pergunta nem aceita o nome da assistente. Depois da
configuração, a primeira conversa real com a IA pergunta exatamente
`Como você quer me chamar?`; só a resposta confirmada cria a identidade.
Se você cancelar uma escolha interativa, o processo termina como cancelado
e não mostra o comando de aplicação. No pedido de login, responder `n` ou
fechar a entrada com Ctrl-D cancela com código `130`, sem iniciar autenticação.

## O que NÃO é

- Não é a instalação inteira: quem confirma o resultado é o instalador adaptativo do Core, não este script.
- Não instala pacotes do sistema automaticamente, não garante chaveiro de credenciais, não promete inferência gratuita, prontidão operacional, skills instaladas nem suporte a provedores arbitrários. As rotas novas e as limitações dos perfis legados estão descritas acima.
- Não exige Claude Code instalado nem diretório `~/.claude`.
- Se o checkout baixado ainda não tiver `instalador/instalar.sh` (instalador adaptativo candidato ainda não publicado nessa versão), o script recusa com o código estável `ADAPTIVE_INSTALLER_UNAVAILABLE` — nunca cai para um caminho antigo.

## Variáveis

`SEXTOU_CORE` (ou, por compatibilidade, `PRIMA_CORE`) escolhe onde o Core fica. Padrão: `~/.sextou/core`.

## Validação local

A suíte usa comandos falsos e diretórios temporários, sem autenticação, rede
ou instalação real. Os testes de terminal exigem PTY em um sistema POSIX.

```bash
python3 -m unittest discover -s tests -v
bash -n install.sh
```

Para avaliar uma instalação real, revise as revisões do bootstrap e do Core,
confirme Git, Node 24+, `gh`, login e acesso ao repositório. O destino deve ser
real, sem links simbólicos; um checkout existente precisa estar limpo e conter
os arquivos do instalador adaptativo. O bootstrap não atualiza esse checkout.
Revise a prévia concluída antes de executar o comando de aplicação apresentado.
Uma prévia ou configuração aplicada ainda não comprova o funcionamento do executor.

---

**Este repositório contém o bootstrap `install.sh`, seus testes e documentação.** É público só porque o servidor de arquivos brutos não entrega repositório privado sem autenticação — a instalação precisa começar de algum lugar.
