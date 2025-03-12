# Microsoft Azure应用程序凭据
CLIENT_ID = "5e4fc304-e251-423b-afca-69fc6fbe093b"  # 应用程序(客户端)ID，从Azure门户获取
CLIENT_SECRET = "P-e8Q~nqnveuvTKFoY9sq6bNTZKVmnBdBr_ygaS6"  # 客户端密钥，从Azure门户的"证书和密钥"部分创建
TENANT_ID = "464ca498-fc9a-4f5a-83dd-3ccbd135965c"  # 租户ID，使用"common"可以支持个人和组织账户

# 重定向URI - 必须与Azure门户中注册的完全一致
REDIRECT_URI = "http://localhost"  # 必须与Azure门户中配置的重定向URI完全匹配

# Microsoft Graph API端点
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["Files.Read", "Files.Read.All"]  # 所需的权限范围

# 本地设置
DOWNLOAD_PATH = "downloads"  # 下载文件的本地目录
TOKEN_CACHE_FILE = "token_cache.json"  # 令牌缓存文件 