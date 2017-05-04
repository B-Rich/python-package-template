
import json, os, re, requests
from lxml.etree import Entity
from bl.url import URL
from bxml import XML
from bxml.builder import Builder
from bf.image import Image

NS = {
    'aid':"http://ns.adobe.com/AdobeInDesign/4.0/",
    'aid5':"http://ns.adobe.com/AdobeInDesign/5.0/",
    'pub':"http://publishingxml.org/ns",
}
E = Builder(**NS)._

path = os.path.dirname(os.path.abspath(__file__))
list_url = "http://recipes.wikia.com/api/v1/Articles/List?category=Dessert_Recipes&limit=100"
articles_url = "http://recipes.wikia.com/api/v1/Articles"
pstylekey = "{%(aid)s}pstyle" % NS
content_path = os.path.join(os.path.dirname(path), 'data')
image_path = os.path.join(content_path, 'images')

def main():
    xml = XML()
    xml.fn = os.path.join(content_path, 'dessert_recipes.xml')
    xml.root = E.items()
    recipe_list = requests.get(list_url).json()
    items = recipe_list.get('items')
    print(len(items), 'items')
    for item in items:
        print(items.index(item), '\t', item.get('id'))
        xml.root.append(get_item_elem(item))
    return xml

def get_item_elem(item):
    attrib = {k:str(item[k]) for k in item.keys()}
    elem = E.item(**attrib)

    details_url = articles_url + '/Details?ids=%(id)s' % attrib
    print(details_url)
    item_details = requests.get(details_url).json()['items'][attrib['id']]
    keys = item_details.keys()
    for key in list(set(['id', 'title', 'type', 'ns']) & set(keys)):
        elem.set(key, str(item_details[key]))
    # if 'thumbnail' in keys and item_details['thumbnail'] is not None:
    #     elem.append(E.thumbnail(src=item_details['thumbnail']))
    # if 'original_dimensions' in keys and item_details.get('original_dimensions') is not None:
    #     dimensions = item_details['original_dimensions']
    #     elem.append(E.image(**{k:str(dimensions[k]) for k in dimensions.keys()}))

    content_url = articles_url + '/AsSimpleJson?id=%(id)s' % attrib
    print(content_url)
    item_content = requests.get(content_url).json()

    for section in item_content.get('sections'):
        elem.append(get_section_elem(section))
    return elem

def get_section_elem(item):
    elem = E.section(**{k:str(item[k]) for k in item.keys() if k in ['title', 'level']})
    # if elem.get('level') is not None and int(elem.get('level')) > 2:
    #     elem.set('level', '2')
    if item.get('title') is not None:
        e = E.title(item.get('title'), Entity('#xA'))
        e.set(pstylekey, 'section-%s-title' % elem.get('level'))
        elem.append(e)
    for image in item.get('images')[:2]:
        img = E.img({'href':image.get('src')})
        md = re.search(r"(^.*\.(?:jpe?g|gif|png|tiff?))", img.get('href'), flags=re.I)
        if md is not None:
            url = md.group()
            result = requests.get(md.group())
            basename = re.sub("%..", "+", os.path.basename(url))
            i = Image(fn=os.path.join(image_path, basename), data=result.content)
            i.write()
            w, h, x, y = i.identify(format="%w,%h,%x,%y").split(',')
            print(w, h, x, y, os.path.basename(i.fn))
            i.mogrify(density="150x150")
            w, h, x, y = i.identify(format="%w,%h,%x,%y").split(',')
            print(w, h, x, y, os.path.basename(i.fn))
            img.set('href', "file://" + os.path.relpath(i.fn, content_path))
            image_elem = E.image(img)
            image_elem.set(pstylekey, 'image')
            elem.append(image_elem)
            if image.get('caption') not in [None, '']:
                elem.append(E.caption(image.get('caption'), Entity('#xA')))
    for content in item.get('content'):
        elem.append(get_content_elem(content, elem))
    return elem

def get_content_elem(item, parent_elem):
    elem = E.content({'type':item.get('type')}, item.get('text') or '')
    if elem.text not in [None, '']: 
        elem.append(Entity("#xA"))
    elem.set(pstylekey, parent_elem.tag + '-' + parent_elem.get('level') + '-' + elem.get('type'))
    for element in item.get('elements') or []:
        elem.append(get_element(element))
    return elem

def get_element(item):
    elem = E.element(item.get('text') or '', *[get_element(i) for i in item.get('elements') or []], Entity('#xA'))
    return elem

if __name__=='__main__':
    xml = main()
    xml.write(pretty_print=True, canonicalized=False)
