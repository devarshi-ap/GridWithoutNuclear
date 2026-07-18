import pandas as pd

try:
    # Create a small sample DataFrame
    df = pd.DataFrame({'Test_Column': [1, 2, 3]})
    print("Pandas is working perfectly!")
    print(df)
except Exception as e:
    print(f"An error occurred: {e}")