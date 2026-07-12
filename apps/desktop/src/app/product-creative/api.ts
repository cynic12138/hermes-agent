export interface ProductCreativeProduct {
  product_id: string
  workspace_path: string
}

export interface ProductCreativeSnapshot {
  product_id: string
  brain: { version?: number; state?: Record<string, unknown>; created_at?: string }
  latest_workflow: Record<string, unknown>
  attention: { pending_proposals: number; open_workflows: number }
}

export interface ProductCreativeWorkflow {
  workflow_id: string
  definition: string
  status: string
  current_step: number
  updated_at: string
  version: number
}

export interface ProductCreativeAsset {
  record_id: string
  type: string
  relative_path: string
  status?: string
  payload: Record<string, unknown>
  created_at: string
}

export interface ProductCreativeLearning {
  versions: Array<Record<string, unknown>>
  rules: Array<Record<string, unknown>>
  proposals: Array<Record<string, unknown>>
}

const prefix = '/api/plugins/product_creative/v1'

function request<T>(workspace: string, path: string, method = 'GET', body?: Record<string, unknown>): Promise<T> {
  return window.hermesDesktop.api<T>({
    path: `${prefix}${path}`,
    method,
    body,
    headers: { 'X-Hermes-Workspace-Root': workspace }
  })
}

export const productCreativeApi = {
  health: (workspace: string) => request<{ ok: boolean; version: string }>(workspace, '/health'),
  products: (workspace: string) => request<{ products: ProductCreativeProduct[] }>(workspace, '/products'),
  snapshot: (workspace: string, product: string) =>
    request<ProductCreativeSnapshot>(workspace, `/products/${encodeURIComponent(product)}/snapshot`),
  workflows: (workspace: string, product: string) =>
    request<{ workflows: ProductCreativeWorkflow[] }>(workspace, `/products/${encodeURIComponent(product)}/workflows`),
  workflow: (workspace: string, id: string) =>
    request<Record<string, unknown>>(workspace, `/workflows/${encodeURIComponent(id)}`),
  reviewQueue: (workspace: string, product: string) =>
    request<{ proposals: Array<Record<string, unknown>>; results: ProductCreativeAsset[] }>(
      workspace,
      `/products/${encodeURIComponent(product)}/review-queue`
    ),
  assets: (workspace: string, product: string) =>
    request<{ artifacts: ProductCreativeAsset[]; materials: ProductCreativeAsset[] }>(
      workspace,
      `/products/${encodeURIComponent(product)}/assets`
    ),
  learning: (workspace: string, product: string) =>
    request<ProductCreativeLearning>(workspace, `/products/${encodeURIComponent(product)}/learning`),
  mutate: (workspace: string, path: string, body: Record<string, unknown>) =>
    request<Record<string, unknown>>(workspace, path, 'POST', body)
}
