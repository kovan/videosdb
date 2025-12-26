FROM debian:bookworm-slim
RUN echo 'root:toor' | chpasswd
ENV DEBIAN_FRONTEND="noninteractive"
RUN apt update
RUN apt install -y curl
RUN apt clean


WORKDIR /app


RUN curl -fsSL https://install.julialang.org | sh

# Copy project files
COPY Project.toml Manifest.toml ./
COPY src/ ./src/

# Install dependencies
RUN julia --project=. -e 'using Pkg; Pkg.instantiate()'

# Precompile
RUN julia --project=. -e 'using Pkg; Pkg.precompile()'

# Set entry point
#ENTRYPOINT ["julia", "--project=.", "src/run.jl"]
#CMD ["--check-for-new-videos"]




COPY  . .




ENTRYPOINT ["poetry"]

