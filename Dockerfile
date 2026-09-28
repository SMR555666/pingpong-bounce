# 必须传入 docker load 加载后的官方镜像名称；不使用通用 PyTorch 镜像替代。
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
WORKDIR /participant
COPY participant/ /participant/
RUN test -f /participant/run_all.sh && chmod +x /participant/run_all.sh
ENTRYPOINT ["/participant/run_all.sh"]
