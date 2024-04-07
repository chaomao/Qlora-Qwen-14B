from modelscope.hub.snapshot_download import snapshot_download
model_dir = snapshot_download('qwen/Qwen-14B', cache_dir='/root/autodl-tmp/jiangxia/base_model/', revision='v1.0.8')
