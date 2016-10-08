"""DOC STRING."""
from bs4 import BeautifulSoup
from pymongo import MongoClient
from time import sleep
import json
import requests


def parseSpecs(spec_list):
    """This function digests a list taken from a product specification table on
    REI's website, and turns it into dictionary object.This function is called
    by productInfoToMDB.

    Args:
        spec_list (list): List from product specification table.

    Returns:
        dic: Dictionary object with key:values relating to product matrial,
        weight, etc.
    """
    dic = {}
    i = 0
    while i < len(spec_list)-2:
        dic[spec_list[i]] = spec_list[i+1]
        i += 2


def productInfoToMDB(collection, url):
    """This function parses product information from each product link in the
    product_links.txt file, and stores the information into a dictionary
    object that is inserted as entry in a product_catagoy specific mongoDB
    collection.

    Args:
        collection (string): Named mongoBD collection.
        url (string): Product link from product_links.txt file.

    Result:
        entry: Inserts a dictionary object as a entry in product_catagory
        specific mongoDB collection.

    NOTE: Not all of the products on REI's website have applicable information.
    Try/except exception handling is used to work around the parsing of missing
    or extraneous information.
    """
    # creates dictionary 'dic'.
    dic = {}
    # temporarily suspends execution to slow rate at which requests are made to url.
    sleep(5)
    # assigns 'r' to website response from specified url.
    r = requests.get(url)
    # creats BeautifulSoup object from website response using lxml parser.
    soup = BeautifulSoup(r.content, 'lxml')
    # assigns the contents of BeautifulSoup object as the value to key 'soup'.
    dic['soup'] = str(soup)
    # assigns CCS selector tag 'title' as value to key 'title'.
    dic['title'] = soup.select('title')[0].text


    try:
        # assigns CCS selector tag as value to key 'description'.
        dic['description'] = soup.select('p.product-primary-description')[0].text.strip()
    except IndexError:
        dic['description'] = 'Product discription not available.'

    try:
        # assigns CCS selector tag as value to key 'description'.
        dic['details'] = soup.select('ul.product-item-details')[0].text.split('\n')
    except IndexError:
        dic['details'] = 'Product details not available.'

    try:
        # assigns CCS selector tag as value to key 'description'.
        dic['specs'] = parseSpecs([u.strip() for u in soup.select('table.product-spec-table')[0].text.split('\n') if u != ''])
    except IndexError:
        dic['specs'] = 'Product specs not available.'

    # decodes 'page-meta-data' element into json string. This object is a dictonary
    # of key:value pairs that contains much of the relevant product information.
    md = json.loads(soup.findAll('script', {'data-client-store': 'page-meta-data'})[0].text)
    # assigns page meta data as vlaue to 'meta_data' key.
    dic['meta_data'] = md

    try:
        # asssigns meta_data 'averageRating' value as value to average_rating key.
        dic['average_rating'] = md['averageRating']
    except:
        dic['average_rating'] = "Product rating not avialable."

    try:
        # assigns the numer of diffrent colors available as the value to 'color_count' key.
        dic['color_count'] = md['pdpcolornum']
    except KeyError:
        dic['color_count'] = 'No color options'

    try:
        # assigns product gender to value of 'gender' key.
        dic['gender'] = md['productGender']
    except KeyError:
        dic['gender'] = 'unisex'

    try:
        # assigns the number of reviews as the value to 'review_count' key.
        dic['review_count'] = md['reviewCount']
    except KeyError:
        dic['review_count'] = "Product rating not avialable."

    try:
        # assigns productCategoryPath value as value for 'product_path' key.
        # example product path: "Products|Men's Clothing|Men's Jackets|Men's Insulated Jackets|Men's Down Jackets"
        dic['product_path'] = md['productCategoryPath']
    except KeyError:
        # Note: Every product should have a product path. Products without a path
        # may no longer be avialable.
        print url
        dic['product_path'] = 'null'

    try:
        # decodes 'page-meta-data' element into json string and returns keys in
        # first level as a list.
        dic['color_list'] = json.loads(soup.findAll('script', {'data-client-store': 'carousel-images'})[0].text).keys()
    except IndexError:
        dic['color_list'] = 'No color options'

    # Adds image paths to 'img_list', and assigns 'img_list' as value to key 'img_list'.
    # example image path: '/media/be1ccefb-97dd-47b2-b189-5e3f32ef25ee?size=2000'
    img_list = []
    for l in soup.findAll('img',{'class': 'product-image-thumbnail'}):
        img_list.append(l['data-high-res-img'])
    dic['img_list'] = img_list

    # inserts dic document into mongoDB collection 'collection'.
    collection.insert_one(dic)


if __name__ == '__main__':
    client = MongoClient()
    db = client.productlinks

    prod_cat = []
    with open('../data/product_catagories.txt', 'r') as cat:
        for line in cat:
            prod_cat.append(line)
    cat.close()

    for cat in prod_cat:
        collection = db.cat
        with open('../data/category_links/' + cat + '-product-links.txt') as cat_links:
            for line in cat_links:
                productInfoToMDB(collection, line.strip())

    client.close()
