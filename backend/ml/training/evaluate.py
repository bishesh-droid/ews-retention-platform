from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
def evaluate_model(model, X_test, y_test):
    y_pred = model.predict(X_test)
    print("\n--- Classification Report ---")
    report = classification_report(y_test, y_pred, target_names=['Graduated (0)', 'Not Graduated (1)'])
    print(report)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Accuracy: {accuracy:.2f}")
    print("\n--- Confusion Matrix ---")
    cm = confusion_matrix(y_test, y_pred)
    print(cm)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=['Predicted Graduated', 'Predicted Not Graduated'],
                yticklabels=['Actual Graduated', 'Actual Not Graduated'])
    plt.title('Confusion Matrix')
    plt.ylabel('Actual Label')
    plt.xlabel('Predicted Label')
    plot_path = 'models/evaluation_confusion_matrix.png'
    plt.savefig(plot_path)
    print(f"\nConfusion matrix plot saved to {plot_path}")
if __name__ == '__main__':
    print("This script is intended to be called by 'train_model.py' after a model has been trained.")
    print("It can also be used for standalone evaluation if you load a model and test data.")
