"""
本脚本演示如何加载一个已经持久化存储的 ChromaDB 向量数据库，
并对其进行相似性搜索查询。

执行流程:
1. 定义一个你想要查询的问题 (query)。
2. 加载与创建数据库时相同的 Embedding 模型。
3. 加载存储在本地磁盘 (./db) 上的向量数据库。
4. 使用 a.similarity_search_with_score 方法执行查询，并打印结果。
"""
import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from pathlib import Path


# --- 配置信息 ---
# 通过 Path(__file__) 获取脚本的绝对路径，然后获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
# 持久化存储路径 (必须与创建时相同)
PERSIST_DIRECTORY = PROJECT_ROOT / "db"
# Embedding 模型 (必须与创建时相同)
EMBEDDING_MODEL = "text-embedding-3-small"


def main():
    """主函数，执行数据库的加载和查询流程"""
    # 加载 .env 文件中的环境变量
    load_dotenv()

    # 检查 OpenAI API key 是否设置
    if not os.getenv("OPENAI_API_KEY"):
        print("错误：OPENAI_API_KEY 环境变量未设置。")
        return

    # 检查数据库目录是否存在
    if not os.path.exists(PERSIST_DIRECTORY):
        print(f"错误：数据库目录 '{PERSIST_DIRECTORY}' 不存在。")
        print("请先运行 'create_vector_database.py' 来创建数据库。")
        return

    # 1. 初始化嵌入模型
    print(f"正在初始化 OpenAI 嵌入模型 ({EMBEDDING_MODEL})...")
    try:
        embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    except Exception as e:
        print(f"初始化嵌入模型时发生错误: {e}")
        return
    print("嵌入模型初始化成功。")

    # 2. 加载持久化的向量数据库
    print(f"正在从 '{PERSIST_DIRECTORY}' 加载向量数据库...")
    try:
        vector_store = Chroma(
            persist_directory=PERSIST_DIRECTORY,
            embedding_function=embeddings
        )
    except Exception as e:
        print(f"加载向量数据库时发生错误: {e}")
        return
    print("数据库加载成功！")

    # 3. 定义你的查询语句
    query = "什么是AI智能体的记忆？它分为哪几种？"
    print(f"你的查询是: {query}")
    print("-" * 50)

    # 4. 执行相似性搜索
    print("正在执行相似性搜索...")
    # 使用 similarity_search_with_score 可以同时返回内容和相似度分数
    # k=3 表示我们希望返回最相似的3个结果
    try:
        results = vector_store.similarity_search_with_score(query, k=3)
    except Exception as e:
        print(f"执行相似性搜索时发生错误: {e}")
        return

    # 5. 打印查询结果
    if not results:
        print("未能找到相关的结果。")
    else:
        print(f"为你找到了 {len(results)} 个最相关的结果：")
        for i, (doc, score) in enumerate(results):
            # ChromaDB 的分数是 L2 距离，分数越小越相关
            print(f"--- 结果 {i+1} (相似度分数: {score:.4f}) ---")
            print(doc.page_content)
            print("")


if __name__ == "__main__":
    main()
