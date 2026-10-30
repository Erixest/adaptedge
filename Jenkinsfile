pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
        disableConcurrentBuilds()
    }

    parameters {
        booleanParam(name: 'PUSH_IMAGE', defaultValue: false,
            description: 'Push the image to the container registry')
        booleanParam(name: 'DEPLOY', defaultValue: true,
            description: 'Deploy to Kubernetes when reachable, otherwise to the local test target')
        string(name: 'IMAGE_REPO', defaultValue: 'ghcr.io/erixest/adaptedge',
            description: 'Registry repository for the published image')
    }

    environment {
        IMAGE_LOCAL  = 'adaptedge'
        IMAGE_TAG    = "${env.BUILD_NUMBER}"
        VENV         = '.venv'
        PYTHON       = '.venv/bin/python'
        PIP          = '.venv/bin/pip'
        CONTAINER    = "adaptedge-ci-${env.BUILD_NUMBER}"
        PORT         = '18080'
        BUILDKIT_HOST = 'unix:///run/user/1000/buildkit/rootless'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    currentBuild.displayName = "#${env.BUILD_NUMBER} ${env.GIT_COMMIT?.take(7)}"
                }
                sh 'git rev-parse --short HEAD && git status --porcelain'
            }
        }

        stage('Toolchain') {
            steps {
                sh 'mkdir -p reports'
                sh 'python3 --version && nerdctl version && java -version'
                sh 'python3 -m venv $VENV'
                sh '$PIP install --upgrade pip'
                sh '$PIP install -e ".[dev]"'
            }
        }

        stage('Lint') {
            steps {
                sh '$VENV/bin/ruff check src tests'
            }
        }

        stage('Unit tests') {
            steps {
                sh '$VENV/bin/pytest -q --junitxml=reports/junit.xml \
                    --cov=adaptedge --cov-report=xml:reports/coverage.xml \
                    --cov-report=term-missing'
            }
        }

        stage('Reproducible evaluation') {
            steps {
                sh '$PYTHON -m adaptedge.evaluate --runs 200 --seed 42 --out reports/metrics.json'
                sh 'cat reports/metrics.json'
            }
        }

        stage('Build image') {
            steps {
                sh 'nerdctl build --tag $IMAGE_LOCAL:$IMAGE_TAG --tag $IMAGE_LOCAL:latest .'
                sh 'nerdctl images $IMAGE_LOCAL'
            }
        }

        stage('Smoke test') {
            steps {
                sh './scripts/smoke_test.sh $IMAGE_LOCAL:$IMAGE_TAG $CONTAINER $PORT'
            }
        }

        stage('Publish image') {
            when { expression { params.PUSH_IMAGE } }
            steps {
                withCredentials([string(credentialsId: 'ghcr-token', variable: 'GHCR_TOKEN')]) {
                    sh 'printf "%s" "$GHCR_TOKEN" | nerdctl login ghcr.io -u Erixest --password-stdin'
                }
                sh 'nerdctl tag $IMAGE_LOCAL:$IMAGE_TAG $IMAGE_REPO:$IMAGE_TAG'
                sh 'nerdctl tag $IMAGE_LOCAL:$IMAGE_TAG $IMAGE_REPO:latest'
                sh 'nerdctl push $IMAGE_REPO:$IMAGE_TAG'
                sh 'nerdctl push $IMAGE_REPO:latest'
            }
        }

        stage('Deploy') {
            when { expression { params.DEPLOY } }
            steps {
                sh './deploy/deploy.sh $IMAGE_LOCAL:$IMAGE_TAG'
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: 'reports/junit.xml'
            archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
            sh 'nerdctl rm -f $CONTAINER >/dev/null 2>&1 || true'
        }
        success {
            echo "Pipeline ${env.BUILD_NUMBER} passed: tests, image, smoke test, publish/deploy stages completed."
        }
        failure {
            echo "Pipeline ${env.BUILD_NUMBER} failed; inspect the stage log and archived reports."
        }
    }
}
