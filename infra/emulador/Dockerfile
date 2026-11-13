# AWS Emulator em contêiner (modo container do ASH). Baseado no Dockerfile da documentação da AWS:
# https://docs.aws.amazon.com/emulator/latest/userguide/getting-started-docker.html (consultado em 13/11/2026).
# A AWS não publica imagem pronta. O ash.py constrói esta imagem com a URL do pacote RPM do perfil de stack
# (bloco emulador_aws), que fixa a versão: python ash.py emulador iniciar.
FROM public.ecr.aws/amazonlinux/amazonlinux:2023-minimal
ARG EMULATOR_RPM_URL
ADD ${EMULATOR_RPM_URL} /tmp/aws-emulator.rpm
RUN rpm -i /tmp/aws-emulator.rpm && rm /tmp/aws-emulator.rpm \
    && mkdir -p /home/emulator && chown 1000 /home/emulator
USER 1000
ENV HOME=/home/emulator
EXPOSE 9297
ENTRYPOINT ["aws-emulator", "-b", "0.0.0.0"]
