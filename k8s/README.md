# Kubernetes Deployment Manifests

This directory contains Kubernetes manifests for deploying the Financial Research Analyst Agent.

## 📁 Files Overview

| File                  | Description                                              |
| --------------------- | -------------------------------------------------------- |
| `namespace.yaml`      | Namespace definition for isolation                       |
| `configmap.yaml`      | Non-sensitive configuration values                       |
| `secret.yaml`         | Template for sensitive credentials (API keys, passwords) |
| `deployment.yaml`     | Main API application deployment                          |
| `service.yaml`        | Service definitions for API, Redis, and PostgreSQL       |
| `ingress.yaml`        | Ingress configuration with TLS and rate limiting         |
| `pvc.yaml`            | Persistent Volume Claims for data persistence            |
| `redis-postgres.yaml` | Redis and PostgreSQL deployments                         |
| `hpa.yaml`            | Horizontal Pod Autoscaler for auto-scaling               |
| `network-policy.yaml` | Network policies for security                            |

## 🚀 Quick Start

### Prerequisites

- Kubernetes cluster (v1.25+)
- `kubectl` configured with cluster access
- Nginx Ingress Controller installed
- TLS certificate (or cert-manager for automatic certificates)

### Deployment Steps

1. **Create the namespace:**

   ```bash
   kubectl apply -f namespace.yaml
   ```

2. **Configure secrets:**

   ```bash
   # Edit secret.yaml and replace placeholder values with base64-encoded secrets
   # Example: echo -n "your-api-key" | base64
   kubectl apply -f secret.yaml
   ```

3. **Apply configuration:**

   ```bash
   kubectl apply -f configmap.yaml
   ```

4. **Create persistent storage:**

   ```bash
   kubectl apply -f pvc.yaml
   ```

5. **Deploy infrastructure components:**

   ```bash
   kubectl apply -f redis-postgres.yaml
   ```

6. **Deploy the application:**

   ```bash
   kubectl apply -f deployment.yaml
   kubectl apply -f service.yaml
   ```

7. **Configure ingress:**

   ```bash
   # Update the host in ingress.yaml to match your domain
   kubectl apply -f ingress.yaml
   ```

8. **Enable auto-scaling:**

   ```bash
   kubectl apply -f hpa.yaml
   ```

9. **Apply network policies (optional but recommended):**
   ```bash
   kubectl apply -f network-policy.yaml
   ```

### One-Command Deployment

Deploy everything at once:

```bash
kubectl apply -f k8s/
```

## 🔧 Configuration

### Updating Secrets

Secrets must be base64 encoded:

```bash
# Encode your API key
echo -n "sk-your-openai-api-key" | base64

# Encode database password
echo -n "your-secure-password" | base64
```

### Customizing Resources

Edit `deployment.yaml` to adjust resource limits:

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

### Scaling

Manual scaling:

```bash
kubectl scale deployment financial-agent-api -n financial-agent --replicas=5
```

The HPA will automatically scale between 2-10 replicas based on load.

## 📊 Monitoring

Check deployment status:

```bash
kubectl get all -n financial-agent
```

View logs:

```bash
kubectl logs -f deployment/financial-agent-api -n financial-agent
```

Check HPA status:

```bash
kubectl get hpa -n financial-agent
```

## 🔒 Security Considerations

1. **Secrets Management**: Consider using external secret management (HashiCorp Vault, AWS Secrets Manager, etc.)
2. **Network Policies**: The included network policy restricts traffic to necessary communications only
3. **RBAC**: Implement Role-Based Access Control for production environments
4. **Pod Security**: Consider adding Pod Security Policies or Pod Security Standards

## 🗑️ Cleanup

Remove all resources:

```bash
kubectl delete -f k8s/
```

Or delete the entire namespace:

```bash
kubectl delete namespace financial-agent
```
