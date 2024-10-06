import os
import sys
import re
from collections import defaultdict, Counter

#------------------------Tokenizer--------------------------------
# Function to process a given line scanned in from a file
def tokenize_line(line):
    pattern = re.compile(r'(".*?"|\w+|[(){}[\];,.\+\-\*\/=<>!]+|\'.*?\')')
    
    tokens = pattern.findall(line)
    separated_tokens = []
    for token in tokens:
        if re.match(r'[(){}[\];,.\+\-\*\/=<>!]+', token):
            separated_tokens.extend(list(token))
        else:
            separated_tokens.append(token)

    # Process quoted strings as these weren't being tokenized properly 
    final_tokens = []
    for token in separated_tokens:
        if token.startswith('"') and token.endswith('"'):
            inner_tokens = re.findall(r'%s' % r'[%\w\d]+|[^\w\s%]', token[1:-1])
            final_tokens.extend(['"' + t + '"' for t in inner_tokens])
        else:
            final_tokens.append(token)

    return final_tokens

# Function to remove comments and tokenize valid Java code
def remove_comments_and_tokenize(java_file):
    tokenized_lines = []
    multi_line_comment = False

    try:
        with open(java_file, 'r', encoding='utf-8') as file:
            lines = file.readlines()
    except UnicodeDecodeError:
        with open(java_file, 'r', encoding='ISO-8859-1') as file:
            lines = file.readlines()

    for line in lines:
        if multi_line_comment:
            if '*/' in line:
                multi_line_comment = False
                line = line.split('*/', 1)[1]
            else:
                continue 

        line = re.sub(r'//.*$', '', line)

        if '/*' in line:
            multi_line_comment = True
            line = line.split('/*', 1)[0]

        line = line.strip()
        if line:
            tokens = tokenize_line(line)
            tokenized_lines.append(' '.join(tokens))

    return tokenized_lines

# Function to process the java files in the corpus directory
def process_directory(directory, output_file):
    with open(output_file, 'w', encoding='utf-8') as out_file:
        for filename in os.listdir(directory):
            if filename.endswith('.java'):
                java_file = os.path.join(directory, filename)
                tokenized_lines = remove_comments_and_tokenize(java_file)
                for tokenized_line in tokenized_lines:
                    out_file.write(tokenized_line + '\n')

#----------------------------Ngram Model----------------------------
#Function to build the model given the file of tokenized java code and the number to tuple tokens.
def build_ngram_model(tokenized_file, n):
    ngram_model = defaultdict(list)

    with open(tokenized_file, 'r', encoding='utf-8') as file:
        for line in file:
            tokens = line.strip().split()
            for i in range(len(tokens) - n + 1):
                ngram = tuple(tokens[i:i + n])
                next_token = tokens[i + n] if i + n < len(tokens) else None
                if next_token:
                    ngram_model[ngram].append(next_token)

    return ngram_model

# Function to attempt to find matches in the ngram and return the 3 most probable
def predict_next_tokens(ngram_model, context):
    context_tuple = tuple(context)
    predictions = ngram_model.get(context_tuple, [])
    count = Counter(predictions)
    return count.most_common(3)

# Function to take in the input java file and scan line by line to attempt to predict what token to inserr 
# after the current token using an ngram model built by the build_ngram_model function
def process_java_file(input_file, n, tokenized_file):
    ngram_model = build_ngram_model(tokenized_file, n)
    output_lines = []

    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if not line:
                    output_lines.append('')
                    continue
                
                tokens = line.split()
                original_line = ' '.join(tokens)
                modified_line = tokens[:]
                total_predictions = 1
                prediction_lines = []

                for index in range(len(tokens)):
                    context = tokens[max(0, index - n + 1):index + 1]
                    predictions = predict_next_tokens(ngram_model, context)
                    
                    if predictions:
                        options = ', '.join([f"{opt[0]} {100 * opt[1] / sum(c for _, c in predictions):.2f}%" for opt in predictions])
                        most_probable_token = predictions[0][0]
                        modified_line.insert(index + total_predictions, most_probable_token)
                        total_predictions += 1
                        prediction_lines.append(f"{' '.join(context)} : ({options})")

                modified_line_str = ' '.join(modified_line)

                output_lines.append(original_line)
                output_lines.append(modified_line_str)
                if total_predictions > 1:
                    output_lines.append("Total number of predictions: " + str(total_predictions-1))
                for pred_line in prediction_lines:
                    output_lines.append(pred_line)
            
                # Padding
                output_lines.append('')
                output_lines.append('')

    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
        return

    output_file = f"processed_{os.path.basename(input_file)}"
    with open(output_file, 'w', encoding='utf-8') as out_file:
        for out_line in output_lines:
            out_file.write(out_line + '\n')

    print(f'Processed file saved as: {output_file}')

#------------------------------Executor------------------------------------
if __name__ == '__main__':
    corpus_directory = 'corpus'
    output_filename = 'tokenized_output.txt'

    input_directory = 'input'
    output_java_filename = 'tokenized_java.txt'
    
    process_directory(corpus_directory, output_filename)
    print(f'All Files Tokenized. Output saved to {output_filename}')

    process_directory(input_directory, output_java_filename)
    print(f'Input File Processed. Output saved to {output_java_filename}')

    n = int(sys.argv[1])
    process_java_file(output_java_filename, n, output_filename)
