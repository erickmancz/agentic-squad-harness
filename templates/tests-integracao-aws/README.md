# Testes de integração do projeto contra o AWS Emulator

Esqueleto para projetos Python que usam serviços AWS (perfil `python-aws`). Não rodam em nenhum CI enquanto estiverem em `templates/`.

1. Ative o perfil: `python ash.py perfil python-aws`, `python ash.py setup` e publique pelo portão `publicar-harness`.
2. Declare o `boto3` com versão exata (`boto3==X.Y.Z`) no `requirements.txt` do projeto: a etapa `dependencias` só audita esse arquivo.
3. Copie `conftest.py` e `test_exemplo_s3.py` para `tests/integracao_aws/` e troque o exemplo pelos testes do projeto, que chamam o código do projeto.
4. Em `perfis/python-aws.json`, ajuste `emulador_aws.servicos` para os serviços que o projeto usa e preencha a fidelidade de cada um (nota "k de n" da página de releases da versão fixada, com fonte e data).
5. Suba o emulador (`python ash.py emulador iniciar`), rode `python ash.py etapa integracao-aws` e pare (`python ash.py emulador parar`).

O `conftest.py` aborta antes de criar qualquer recurso se o endpoint não for `https://127.0.0.1:<porta>` ou se as credenciais não forem as geradas pelo emulador. Nada aqui toca conta AWS real. Passo a passo e regras completas: `README.md` do repositório, seção "Testes contra o AWS Emulator".
