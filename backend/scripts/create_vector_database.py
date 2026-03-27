"""
本脚本负责创建并持久化存储知识库的向量数据库。

执行流程:
1. 从 ./knowledge_base 目录加载所有 Markdown 文档。
2. 将加载的文档切分成较小的、语义完整的文本块 (chunks)。
3. 使用 OpenAI 的 embedding 模型将文本块转换为向量。
4. 将向量和文本块存入本地的 ChromaDB 数据库中，并持久化到 ./db 目录。
"""
import os
import shutil
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from pathlib import Path


# --- 配置信息 ---
# 通过 Path(__file__) 获取脚本的绝对路径，然后获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
# 知识库目录
KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "knowledge_base"
# 持久化存储路径
PERSIST_DIRECTORY = PROJECT_ROOT / "db"
# Embedding 模型
EMBEDDING_MODEL = "text-embedding-3-small"


def main():
    """主函数，执行向量数据库的创建流程"""
    # 加载 .env 文件中的环境变量，主要是 OPENAI_API_KEY
    load_dotenv()
    
    # 检查 OpenAI API key 是否设置
    if not os.getenv("OPENAI_API_KEY"):
        print("错误：OPENAI_API_KEY 环境变量未设置。")
        print("请在项目根目录创建一个 .env 文件并添加您的 API 密钥。")
        return

    # 检查知识库目录是否存在且不为空
    if not os.path.exists(KNOWLEDGE_BASE_DIR) or not os.listdir(KNOWLEDGE_BASE_DIR):
        print(f"错误：知识库目录 '{KNOWLEDGE_BASE_DIR}' 不存在或为空。")
        print("请先在该目录中放入您的 Markdown 笔记文件。")
        return

    # 如果持久化目录已存在，先删除，确保每次都创建全新的数据库
    if os.path.exists(PERSIST_DIRECTORY):
        print(f"检测到旧的数据库目录 '{PERSIST_DIRECTORY}'，正在删除...")
        shutil.rmtree(PERSIST_DIRECTORY)
        print("旧数据库已删除。")

    # 1. 加载文档
    print(f"正在从 '{KNOWLEDGE_BASE_DIR}' 加载文档...")
    loader = DirectoryLoader(KNOWLEDGE_BASE_DIR, glob="**/*.md", show_progress=True, loader_kwargs={'autodetect_encoding': True})
    try:
        documents = loader.load()
        if not documents:
            print("警告：未加载到任何文档。请检查目录和文件格式。")
            return
        print(f"成功加载 {len(documents)} 篇文档。")
    except Exception as e:
        print(f"加载文档时发生错误: {e}")
        return

    # 2. 切分文档
    print("正在切分文档...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = text_splitter.split_documents(documents)
    print(f"文档被切分为 {len(chunks)} 个片段。")

    # 3. 初始化嵌入模型
    print(f"正在初始化 OpenAI 嵌入模型 ({EMBEDDING_MODEL})...")
    try:
        embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        print("嵌入模型初始化成功。")
    except Exception as e:
        print(f"初始化嵌入模型时发生错误: {e}")
        return

    # 4. 创建并持久化向量数据库
    print(f"正在创建向量数据库并持久化存储到 '{PERSIST_DIRECTORY}'...")
    try:
        vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=PERSIST_DIRECTORY
        )
        print(f"向量数据库成功创建！")
    except Exception as e:
        print(f"创建向量数据库时发生错误: {e}")
        return
    
    print("索引过程完成！现在你可以运行主程序来使用这个知识库了。")


if __name__ == "__main__":
    main()
