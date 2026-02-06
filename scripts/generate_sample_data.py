import pandas as pd
import numpy as np
import random

def generate_student_data(num_students=5000):
    data = []
    for i in range(1, num_students + 1):
        student_id = f"S{i:05d}"
        
        # Initialize metrics for the student
        absrates = {}
        nsusps = {}
        mobilities = {}
        qmpas = {}
        
        # Introduce some base performance/risk for the student
        # Higher base_risk -> more likely to have higher absrate, nsusp, mobility, lower mpa, and eventually nograd=1
        base_risk = random.uniform(0, 1) # 0 to 1, higher means more at-risk tendencies
        
        # Generate data for 7 years
        for year in range(1, 8):
            # Absrate: higher for higher base_risk
            absrates[f'absrate{year}'] = round(max(0, min(30, base_risk * 40 + random.uniform(-5, 5))), 2)
            
            # Nsusp: higher for higher base_risk
            nsusps[f'nsusp{year}'] = random.randint(0, max(1, min(5, int(base_risk * 8 + random.uniform(-1, 1)))))
            
            # Mobility: higher for higher base_risk
            mobilities[f'mobility{year}'] = random.randint(0, max(0, min(3, int(base_risk * 5 + random.uniform(-0.5, 0.5)))))
            
            # MPA: lower for higher base_risk
            for q in range(1, 5):
                qmpas[f'q{q}mpa{year}'] = round(max(40, min(100, 90 - base_risk * 30 + random.uniform(-10, 10))), 2)
        
        # Determine nograd based on cumulative risk factors, especially in later years
        # More likely to nograd if consistently high absrate, nsusp, mobility and low mpa
        
        # Calculate an aggregate risk score over the years
        total_absrate = sum(absrates.values())
        total_nsusp = sum(nsusps.values())
        total_mobility = sum(mobilities.values())
        avg_mpa = np.mean(list(qmpas.values())) if qmpas else 0
        
        # Combine risk factors for nograd decision
        # Giving more weight to later years and general poor performance
        # A simple linear combination for demonstration
        risk_factor = (total_absrate * 0.05) + (total_nsusp * 0.5) + (total_mobility * 0.7) + (100 - avg_mpa) * 0.1
        
        nograd = 0
        # Set a threshold for nograd. Adjust this to control imbalance.
        # Approx 10-15% will be nograd=1
        if risk_factor > 15 + random.uniform(-5, 5): # Add randomness to make it less deterministic
            nograd = 1
        
        student_data = {'id': student_id, **absrates, **nsusps, **mobilities, **qmpas, 'nograd': nograd}
        data.append(student_data)
        
    df = pd.DataFrame(data)
    return df

if __name__ == '__main__':
    csv_output_path = 'frontend/public/data/student_data_test.csv'
    num_students_to_generate = 5000
    
    print(f"Generating {num_students_to_generate} student records...")
    new_df = generate_student_data(num_students_to_generate)
    
    # Ensure 'nograd' is integer type if it's treated as such
    new_df['nograd'] = new_df['nograd'].astype(int)
    
    new_df.to_csv(csv_output_path, index=False)
    print(f"New student data CSV file created at: {csv_output_path}")
    
    # Print some statistics about the generated data
    print("\n--- Generated Data Statistics ---")
    print(f"Total students: {len(new_df)}")
    print(f"Students with nograd=1: {new_df['nograd'].sum()}")
    print(f"Percentage nograd=1: {new_df['nograd'].mean() * 100:.2f}%")
    print(f"Average q4mpa7 for nograd=1: {new_df[new_df['nograd']==1]['q4mpa7'].mean():.2f}")
    print(f"Average q4mpa7 for nograd=0: {new_df[new_df['nograd']==0]['q4mpa7'].mean():.2f}")
    print(f"Average absrate7 for nograd=1: {new_df[new_df['nograd']==1]['absrate7'].mean():.2f}")
    print(f"Average absrate7 for nograd=0: {new_df[new_df['nograd']==0]['absrate7'].mean():.2f}")
